"""Cover manager for HomeShift integration.

Handles cover heat-protection (closing covers when it gets too hot) and
the native daily open/close schedule for a cover group. Heat protection's
active window is fully derived from the daily schedule's computed open/close
times, so it is inert until the daily schedule is configured.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time as dt_time, timedelta
from typing import TYPE_CHECKING, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_COVER_ENTITIES,
    CONF_COVER_TEMP_SENSOR,
    CONF_COVER_TEMP_THRESHOLD,
    CONF_COVER_ACTION,
    CONF_COVER_MY_BUTTON,
    DEFAULT_COVER_TEMP_THRESHOLD,
    DEFAULT_COVER_ACTION,
    CONF_COVER_WEATHER_ENTITY,
    CONF_COVER_FORECAST_THRESHOLD,
    DEFAULT_COVER_FORECAST_THRESHOLD,
    CONF_DAILY_COVER_ENTITIES,
    CONF_DAILY_COVER_OPEN_TIME_MAP,
    CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES,
    DEFAULT_DAILY_COVER_OPEN_TIME,
    DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES,
    CONF_SUNRISE_EARLIEST,
    DEFAULT_SUNRISE_EARLIEST,
)

if TYPE_CHECKING:
    from homeassistant.core import Event

_LOGGER = logging.getLogger(__name__)

# Persistent storage — survives HA restarts so a mid-day reboot doesn't lose
# track of which covers this automation already closed today.
STORAGE_VERSION = 1
STORAGE_KEY = f"{__name__}.state"


def _parse_time_str(time_str: str) -> dt_time | None:
    """Parse 'HH:MM' or 'HH:MM:SS' string into a time object.

    Returns None if the string cannot be parsed.
    """
    if not time_str:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def _parse_stored_date(value: str | None) -> date | None:
    """Parse an ISO 'YYYY-MM-DD' string into a date. Returns None if unparseable."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_mode_map(raw: str) -> dict[str, str]:
    """Parse a 'Key:Value, Key:Value, ...' string into a dict."""
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, _, value = pair.partition(":")
            result[key.strip()] = value.strip()
    return result


class CoverManager:
    """Manages cover heat-protection and the native daily open/close schedule."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self.cover_open_time: str | None = None
        self.daily_close_time: str | None = None
        # Heat protection state — whether the heat-protected cover has been
        # closed by this automation today (proactively or reactively). Once
        # closed, it stays closed for the rest of the day: heat protection
        # never reopens it — only the next day's normal open (which resets
        # this flag) or the daily schedule's own unconditional evening close
        # touch the cover again.
        self._heat_closed: bool = False
        self._proactive_checked_date: date | None = None
        # Once-per-day tracking for the native daily open/close schedule
        # (separate cover group from heat protection).
        self._daily_opened_date: date | None = None
        self._daily_closed_date: date | None = None
        self._store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")

    @property
    def _config(self) -> dict:
        """Return merged config: entry.data overridden by entry.options."""
        return {**self._entry.data, **self._entry.options}

    async def async_restore_state(self) -> None:
        """Restore persisted cover-automation state from storage.

        Called once during setup, before the first check, so a HA restart
        mid-day doesn't lose track of the day's state (e.g. whether the
        heat-protected cover is currently closed, or whether today's daily
        open/close already ran).
        """
        try:
            stored = await self._store.async_load()
        except Exception as err:  # noqa: BLE001 - defensive around storage I/O
            _LOGGER.warning("Cover manager: could not load persisted state: %s", err)
            return

        if not stored:
            return

        self._heat_closed = bool(stored.get("heat_closed", False))
        self._proactive_checked_date = _parse_stored_date(stored.get("proactive_checked_date"))
        self._daily_opened_date = _parse_stored_date(stored.get("daily_opened_date"))
        self._daily_closed_date = _parse_stored_date(stored.get("daily_closed_date"))

    async def _async_save_state(self) -> None:
        """Persist cover-automation state to storage."""
        try:
            await self._store.async_save(
                {
                    "heat_closed": self._heat_closed,
                    "proactive_checked_date": self._proactive_checked_date.isoformat() if self._proactive_checked_date else None,
                    "daily_opened_date": self._daily_opened_date.isoformat() if self._daily_opened_date else None,
                    "daily_closed_date": self._daily_closed_date.isoformat() if self._daily_closed_date else None,
                }
            )
        except Exception as err:  # noqa: BLE001 - defensive around storage I/O
            _LOGGER.warning("Cover manager: could not persist state: %s", err)

    def async_setup_listeners(self) -> Callable[[], None]:
        """Register a state-change listener on the temperature sensor.

        When the sensor value changes, heat protection is checked immediately
        rather than waiting for the next coordinator poll.
        Returns an unsub callable to register with entry.async_on_unload.
        """
        temp_sensor = self._config.get(CONF_COVER_TEMP_SENSOR, "")
        if not temp_sensor:
            return lambda: None

        @callback
        def _on_temp_change(_event: Event[EventStateChangedData]) -> None:
            self._hass.async_create_task(self.async_check_heat_protection(dt_util.now()))

        _LOGGER.debug("Cover heat protection: listening for changes on '%s'", temp_sensor)
        return async_track_state_change_event(self._hass, [temp_sensor], _on_temp_change)

    def _is_within_daily_window(self, now: datetime) -> bool:
        """Return True when now falls between cover_open_time and daily_close_time."""
        if self.cover_open_time is None or self.daily_close_time is None:
            return False
        open_time = _parse_time_str(self.cover_open_time)
        close_time = _parse_time_str(self.daily_close_time)
        if open_time is None or close_time is None:
            return False
        return open_time <= now.time() <= close_time

    async def async_check_heat_protection(self, now: datetime) -> None:
        """Run proactive and reactive heat protection for the configured cover.

        The active window is derived entirely from the Daily Cover Schedule's
        computed cover_open_time/daily_close_time — heat protection does
        nothing until that feature is configured and has computed today's
        times. Within the window, the cover closes when the temperature
        exceeds the threshold (or, once per day at cover_open_time, when
        today's forecast high does). It never reopens itself once closed —
        it stays closed for the rest of the day; only the next day's normal
        open (or the daily schedule's own unconditional evening close)
        touches it again.
        """
        cover_entities = self._config.get(CONF_COVER_ENTITIES, [])
        temp_sensor = self._config.get(CONF_COVER_TEMP_SENSOR, "")

        if not cover_entities or not temp_sensor:
            return

        if self.cover_open_time is None or self.daily_close_time is None:
            _LOGGER.debug(
                "Cover heat protection: waiting on Daily Cover Schedule's computed "
                "open/close times (not configured yet, or not computed today)"
            )
            return

        await self._async_check_proactive_close(now, cover_entities)
        await self._async_check_reactive_close(now, cover_entities, temp_sensor)

    async def _async_apply_cover_action(self, cover_entities: list[str]) -> None:
        """Press the configured My button, or call the configured cover service."""
        my_button = self._config.get(CONF_COVER_MY_BUTTON, "")

        if my_button:
            await self._hass.services.async_call(
                "button",
                "press",
                {"entity_id": my_button},
                blocking=False,
            )
            return

        configured_cover_action = self._config.get(CONF_COVER_ACTION, DEFAULT_COVER_ACTION)
        allowed_cover_actions = {"close_cover", "stop_cover"}
        cover_action = configured_cover_action if configured_cover_action in allowed_cover_actions else DEFAULT_COVER_ACTION
        if configured_cover_action not in allowed_cover_actions:
            _LOGGER.warning(
                "Cover heat protection: invalid cover action '%s', falling back to '%s'",
                configured_cover_action,
                DEFAULT_COVER_ACTION,
            )
        await self._hass.services.async_call(
            "cover",
            cover_action,
            {"entity_id": cover_entities},
            blocking=False,
        )

    async def _async_check_proactive_close(self, now: datetime, cover_entities: list[str]) -> None:
        """Close the cover ahead of time when today's forecast high is hot enough.

        Reactive closing (temperature > threshold) only fires once the outdoor
        air is already hot — by then a south-facing room has often already
        absorbed hours of solar/conductive gain that a later closure can't
        undo. Checking the day's forecast once, at cover_open_time, lets the
        cover close before that gain happens (or skip the open->close flicker
        entirely if it's already known to be a hot day).
        Runs at most once per calendar day; a failed forecast lookup is
        retried on the next call instead of being marked done.
        """
        weather_entity = self._config.get(CONF_COVER_WEATHER_ENTITY, "")
        if not weather_entity:
            return

        today = now.date()
        if self._proactive_checked_date == today:
            return

        open_time = _parse_time_str(self.cover_open_time)
        if open_time is None or now.time() < open_time:
            return

        forecast_high = await self._async_get_forecast_high(weather_entity)
        if forecast_high is None:
            return

        self._proactive_checked_date = today

        threshold = float(self._config.get(CONF_COVER_FORECAST_THRESHOLD, DEFAULT_COVER_FORECAST_THRESHOLD))
        if forecast_high <= threshold:
            await self._async_save_state()
            return

        _LOGGER.info(
            "Cover proactive close: forecast high=%.1f > threshold=%.1f, closing covers %s",
            forecast_high,
            threshold,
            cover_entities,
        )
        await self._async_apply_cover_action(cover_entities)
        self._heat_closed = True
        await self._async_save_state()

    async def _async_get_forecast_high(self, weather_entity: str) -> float | None:
        """Return today's forecast high temperature for weather_entity, or None on failure."""
        try:
            response = await self._hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": weather_entity, "type": "daily"},
                blocking=True,
                return_response=True,
            )
        except Exception as err:  # noqa: BLE001 - defensive boundary around an external service call
            _LOGGER.warning("Cover proactive close: get_forecasts failed for '%s': %s", weather_entity, err)
            return None

        forecasts = (response or {}).get(weather_entity, {}).get("forecast") or []
        if not forecasts:
            return None

        try:
            return float(forecasts[0].get("temperature"))
        except (TypeError, ValueError):
            return None

    async def _async_check_reactive_close(self, now: datetime, cover_entities: list[str], temp_sensor: str) -> None:
        """Close the cover when the outdoor temperature exceeds the threshold.

        Only acts within the active window, and only once per day — once
        closed by this automation, it's left alone for the rest of the day
        (see async_check_heat_protection).
        """
        if self._heat_closed:
            return

        if not self._is_within_daily_window(now):
            return

        temp_state = self._hass.states.get(temp_sensor)
        if temp_state is None:
            return

        try:
            temperature = float(temp_state.state)
        except (ValueError, TypeError):
            return

        threshold = float(self._config.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD))
        if temperature <= threshold:
            return

        _LOGGER.info(
            "Cover heat protection: temperature=%.1f > threshold=%.1f, closing covers %s",
            temperature,
            threshold,
            cover_entities,
        )
        await self._async_apply_cover_action(cover_entities)
        self._heat_closed = True
        await self._async_save_state()

    def is_heat_protection_active(self, now: datetime) -> bool | None:
        """Return whether heat protection conditions are currently met.

        Returns True  when: within the daily open/close window AND temperature > threshold.
        Returns False when: outside the window, or within it but temp <= threshold.
        Returns None  when: not configured, Daily Cover Schedule hasn't computed
                             today's times yet, sensor unavailable, or unparseable values.
        """
        cover_entities = self._config.get(CONF_COVER_ENTITIES, [])
        temp_sensor = self._config.get(CONF_COVER_TEMP_SENSOR, "")

        if not cover_entities or not temp_sensor:
            return None

        if self.cover_open_time is None or self.daily_close_time is None:
            return None

        if not self._is_within_daily_window(now):
            return False

        temp_state = self._hass.states.get(temp_sensor)
        if temp_state is None:
            return None

        try:
            temperature = float(temp_state.state)
        except (ValueError, TypeError):
            return None

        threshold = float(self._config.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD))
        return temperature > threshold

    def _get_next_sun_time(self, attr_name: str) -> dt_time | None:
        """Return the local time-of-day for a sun.sun 'next_*' attribute, or None."""
        sun_state = self._hass.states.get("sun.sun")
        if sun_state is None:
            return None

        raw = sun_state.attributes.get(attr_name)
        if not raw:
            return None

        try:
            local_dt = dt_util.as_local(datetime.fromisoformat(str(raw)))
        except (ValueError, TypeError):
            return None

        return _parse_time_str(local_dt.strftime("%H:%M"))

    async def async_compute_daily_schedule(self, now: datetime, day_mode_key: str | None) -> None:
        """Compute today's open/close times for the native daily cover schedule.

        The open time is resolved from CONF_DAILY_COVER_OPEN_TIME_MAP for
        today's day_mode_key: 'sunrise' (floored at CONF_SUNRISE_EARLIEST),
        'skip' (no automatic opening today — sets cover_open_time to None),
        or a fixed 'HH:MM' time. A mode missing from the map falls back to
        DEFAULT_DAILY_COVER_OPEN_TIME.
        Close time is always today's sunset plus CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES
        — unlike opening, closing is not mode-dependent.
        Called once when a new calendar day is detected. Computed once per
        day — a day-mode change later that same day does not recompute the
        open time. Also resets heat protection's closed state for the new day.
        """
        self._heat_closed = False

        if not self._config.get(CONF_DAILY_COVER_ENTITIES, []):
            return

        open_time_map = _parse_mode_map(self._config.get(CONF_DAILY_COVER_OPEN_TIME_MAP, ""))
        raw_value = open_time_map.get(day_mode_key or "", DEFAULT_DAILY_COVER_OPEN_TIME).strip().lower()

        if raw_value == "skip":
            self.cover_open_time = None
        elif raw_value == "sunrise":
            sunrise_time = self._get_next_sun_time("next_rising")
            earliest_time = _parse_time_str(self._config.get(CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST))
            if sunrise_time is not None and earliest_time is not None:
                target = sunrise_time if sunrise_time > earliest_time else earliest_time
                self.cover_open_time = target.strftime("%H:%M")
            else:
                _LOGGER.warning("Daily cover schedule: could not determine sunrise/earliest open time")
                self.cover_open_time = None
        else:
            open_time = _parse_time_str(raw_value)
            if open_time is not None:
                self.cover_open_time = open_time.strftime("%H:%M")
            else:
                _LOGGER.warning(
                    "Daily cover schedule: could not parse open time '%s' for mode '%s'", raw_value, day_mode_key
                )
                self.cover_open_time = None

        sunset_time = self._get_next_sun_time("next_setting")
        if sunset_time is not None:
            offset = int(self._config.get(CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES, DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES))
            close_dt = datetime.combine(now.date(), sunset_time) + timedelta(minutes=offset)
            self.daily_close_time = close_dt.strftime("%H:%M")
        else:
            _LOGGER.warning("Daily cover schedule: could not determine sunset time")
            self.daily_close_time = None

        _LOGGER.info(
            "Daily cover schedule: open_time=%s, close_time=%s (day_mode=%s)",
            self.cover_open_time,
            self.daily_close_time,
            day_mode_key,
        )

    async def async_check_daily_schedule(self, now: datetime) -> None:
        """Open covers at today's computed open time, close them at the computed close time.

        Targets CONF_DAILY_COVER_ENTITIES (typically a cover group) — a
        separate entity list from CONF_COVER_ENTITIES used by heat protection,
        so a single unitary cover can stay under heat-protection's control
        while the group follows the daily open/close schedule.
        Each action fires at most once per calendar day. cover_open_time is
        None when today's mode resolved to 'skip' (see
        async_compute_daily_schedule), which naturally skips the open below.
        Closing is unconditional — it always happens once per day regardless
        of mode.
        """
        daily_entities = self._config.get(CONF_DAILY_COVER_ENTITIES, [])
        if not daily_entities:
            return

        today = now.date()

        if self._daily_opened_date != today and self.cover_open_time:
            open_time = _parse_time_str(self.cover_open_time)
            if open_time is not None and now.time() >= open_time:
                _LOGGER.info(
                    "Daily cover schedule: opening covers %s (open_time=%s)",
                    daily_entities,
                    self.cover_open_time,
                )
                await self._hass.services.async_call(
                    "cover", "open_cover", {"entity_id": daily_entities}, blocking=False
                )
                self._daily_opened_date = today
                await self._async_save_state()

        if self._daily_closed_date != today and self.daily_close_time:
            close_time = _parse_time_str(self.daily_close_time)
            if close_time is not None and now.time() >= close_time:
                _LOGGER.info(
                    "Daily cover schedule: closing covers %s (close_time=%s)",
                    daily_entities,
                    self.daily_close_time,
                )
                await self._hass.services.async_call(
                    "cover", "close_cover", {"entity_id": daily_entities}, blocking=False
                )
                self._daily_closed_date = today
                await self._async_save_state()
