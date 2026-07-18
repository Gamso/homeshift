"""Cover manager for HomeShift integration.

Handles cover heat-protection (closing covers when it gets too hot) and
sunrise-based scheduler adjustment.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time as dt_time
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
    CONF_COVER_TIME_START,
    CONF_COVER_TIME_END,
    CONF_COVER_ACTION,
    CONF_COVER_MY_BUTTON,
    DEFAULT_COVER_TEMP_THRESHOLD,
    DEFAULT_COVER_TIME_START,
    DEFAULT_COVER_TIME_END,
    DEFAULT_COVER_ACTION,
    CONF_COVER_WEATHER_ENTITY,
    CONF_COVER_FORECAST_THRESHOLD,
    DEFAULT_COVER_FORECAST_THRESHOLD,
    CONF_COVER_EVENING_REOPEN_TEMP,
    DEFAULT_COVER_EVENING_REOPEN_TEMP,
    CONF_SUNRISE_SCHEDULERS,
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


class CoverManager:
    """Manages cover heat-protection and sunrise-based scheduler adjustment."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self.cover_open_time: str | None = None
        # Tracks which day each once-per-day action last ran on, so proactive
        # closing and evening reopening each fire at most once per calendar day.
        self._proactive_checked_date: date | None = None
        self._closed_date: date | None = None
        self._reopened_date: date | None = None
        self._store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")

    @property
    def _config(self) -> dict:
        """Return merged config: entry.data overridden by entry.options."""
        return {**self._entry.data, **self._entry.options}

    async def async_restore_state(self) -> None:
        """Restore the once-per-day action dates from storage.

        Called once during setup, before the first check, so a HA restart
        between the proactive close and the evening reopen doesn't silently
        disable the reopen for the rest of that day.
        """
        try:
            stored = await self._store.async_load()
        except Exception as err:  # noqa: BLE001 - defensive around storage I/O
            _LOGGER.warning("Cover manager: could not load persisted state: %s", err)
            return

        if not stored:
            return

        self._proactive_checked_date = _parse_stored_date(stored.get("proactive_checked_date"))
        self._closed_date = _parse_stored_date(stored.get("closed_date"))
        self._reopened_date = _parse_stored_date(stored.get("reopened_date"))

    async def _async_save_state(self) -> None:
        """Persist the once-per-day action dates to storage."""
        try:
            await self._store.async_save(
                {
                    "proactive_checked_date": self._proactive_checked_date.isoformat() if self._proactive_checked_date else None,
                    "closed_date": self._closed_date.isoformat() if self._closed_date else None,
                    "reopened_date": self._reopened_date.isoformat() if self._reopened_date else None,
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

    async def async_check_heat_protection(self, now: datetime) -> None:
        """Run the configured cover action when temperature exceeds the threshold in the window.

        Reads CONF_COVER_ENTITIES, CONF_COVER_TEMP_SENSOR, CONF_COVER_TEMP_THRESHOLD,
        CONF_COVER_TIME_START, CONF_COVER_TIME_END, and CONF_COVER_ACTION from the
        config entry.
        When the current time falls inside the window and the temperature is above
        the threshold, it calls the configured cover service (default: close_cover)
        on all configured cover entities.

        Also runs the proactive forecast-based close and the automatic evening
        reopen, since both are cheap no-ops once already handled for the day and
        this method is already called on every sensor change and coordinator poll.
        """

        cover_entities = self._config.get(CONF_COVER_ENTITIES, [])
        temp_sensor = self._config.get(CONF_COVER_TEMP_SENSOR, "")

        if not cover_entities or not temp_sensor:
            return

        await self._async_check_proactive_close(now, cover_entities)
        await self._async_check_evening_reopen(now, cover_entities)

        active = self.is_heat_protection_active(now)
        if not active:
            return

        temp_state = self._hass.states.get(temp_sensor)
        temperature = float(temp_state.state) if temp_state else 0.0
        threshold = float(self._config.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD))

        _LOGGER.info(
            "Cover heat protection: temperature=%.1f > threshold=%.1f, reacting on covers %s",
            temperature,
            threshold,
            cover_entities,
        )
        await self._async_apply_cover_action(cover_entities)
        self._closed_date = now.date()
        await self._async_save_state()

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
        """Close covers ahead of time when today's forecast high is hot enough.

        Reactive closing (temperature > threshold) only fires once the outdoor
        air is already hot — by then a south-facing room has often already
        absorbed hours of solar/conductive gain that a later closure can't
        undo. Checking the day's forecast once, at CONF_COVER_TIME_START,
        lets the cover close before that gain happens.
        Runs at most once per calendar day; a failed forecast lookup is
        retried on the next call instead of being marked done.
        """
        weather_entity = self._config.get(CONF_COVER_WEATHER_ENTITY, "")
        if not weather_entity:
            return

        today = now.date()
        if self._proactive_checked_date == today:
            return

        time_start = _parse_time_str(self._config.get(CONF_COVER_TIME_START, DEFAULT_COVER_TIME_START))
        if time_start is None or now.time() < time_start:
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
        self._closed_date = today
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

    async def _async_check_evening_reopen(self, now: datetime, cover_entities: list[str]) -> None:
        """Reopen covers the heat-protection automation closed, once it has cooled down.

        Only reopens covers that this automation itself closed today (proactively
        or reactively), only after CONF_COVER_TIME_END, and only once per day —
        it never touches a cover the user closed manually for other reasons.
        """
        today = now.date()
        if self._closed_date != today or self._reopened_date == today:
            return

        time_end = _parse_time_str(self._config.get(CONF_COVER_TIME_END, DEFAULT_COVER_TIME_END))
        if time_end is None or now.time() < time_end:
            return

        temp_sensor = self._config.get(CONF_COVER_TEMP_SENSOR, "")
        temp_state = self._hass.states.get(temp_sensor)
        if temp_state is None:
            return

        try:
            temperature = float(temp_state.state)
        except (ValueError, TypeError):
            return

        reopen_temp = float(self._config.get(CONF_COVER_EVENING_REOPEN_TEMP, DEFAULT_COVER_EVENING_REOPEN_TEMP))
        if temperature > reopen_temp:
            return

        _LOGGER.info(
            "Cover evening reopen: temperature=%.1f <= %.1f, opening covers %s",
            temperature,
            reopen_temp,
            cover_entities,
        )
        await self._hass.services.async_call(
            "cover",
            "open_cover",
            {"entity_id": cover_entities},
            blocking=False,
        )
        self._reopened_date = today
        await self._async_save_state()

    def is_heat_protection_active(self, now: datetime) -> bool | None:
        """Return whether heat protection conditions are currently met.

        Returns True  when: within time window AND temperature > threshold.
        Returns False when: outside time window, or within window but temp <= threshold.
        Returns None  when: not configured, sensor unavailable, or unparseable values.
        """
        cover_entities = self._config.get(CONF_COVER_ENTITIES, [])
        temp_sensor = self._config.get(CONF_COVER_TEMP_SENSOR, "")

        if not cover_entities or not temp_sensor:
            return None

        time_start_str = self._config.get(CONF_COVER_TIME_START, DEFAULT_COVER_TIME_START)
        time_end_str = self._config.get(CONF_COVER_TIME_END, DEFAULT_COVER_TIME_END)
        time_start = _parse_time_str(time_start_str)
        time_end = _parse_time_str(time_end_str)

        if time_start is None or time_end is None:
            return None

        now_time = now.time()
        if not time_start <= now_time <= time_end:
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

    async def async_adjust_sunrise_schedulers(self) -> None:
        """Adjust scheduler timeslots based on today's sunrise time.

        For each scheduler entity listed in CONF_SUNRISE_SCHEDULERS, compute:
            target_time = max(sunrise, CONF_SUNRISE_EARLIEST)
        and update its first timeslot start via the scheduler.edit service.

        Called automatically when a new calendar day is detected in the coordinator
        so that schedulers are updated shortly after midnight.
        """
        sunrise_schedulers = self._config.get(CONF_SUNRISE_SCHEDULERS, [])
        if not sunrise_schedulers:
            return

        earliest_str = self._config.get(CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST)
        earliest_time = _parse_time_str(earliest_str)
        if earliest_time is None:
            _LOGGER.warning(
                "Sunrise adjustment: cannot parse earliest time '%s'", earliest_str
            )
            return

        sun_state = self._hass.states.get("sun.sun")
        if sun_state is None:
            _LOGGER.warning(
                "Sunrise adjustment: sun.sun entity not found, skipping"
            )
            return

        next_rising = sun_state.attributes.get("next_rising")
        if not next_rising:
            _LOGGER.warning(
                "Sunrise adjustment: sun.sun has no next_rising attribute"
            )
            return

        try:
            next_rising_dt = datetime.fromisoformat(str(next_rising))
            sunrise_local = dt_util.as_local(next_rising_dt)
            sunrise_str = sunrise_local.strftime("%H:%M")
            sunrise_time = _parse_time_str(sunrise_str)
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Sunrise adjustment: cannot parse next_rising: %s", err)
            return

        if sunrise_time is None:
            return

        # Use whichever is later: sunrise or the configured earliest
        earliest_hhmm = earliest_time.strftime("%H:%M")
        target_time = sunrise_str if sunrise_time > earliest_time else earliest_hhmm
        self.cover_open_time = target_time

        for entity_id in sunrise_schedulers:
            state = self._hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning(
                    "Sunrise adjustment: scheduler entity '%s' not found", entity_id
                )
                continue

            actions: list = list(state.attributes.get("actions") or [])
            entities: list = list(state.attributes.get("entities") or [])

            if not actions:
                _LOGGER.warning(
                    "Sunrise adjustment: scheduler '%s' has no actions, skipping",
                    entity_id,
                )
                continue

            # Merge the cover entity_id into the action dict (mirrors the original
            # automation: dict(current_action, **{'entity_id': current_entity}))
            current_action: dict = dict(actions[0])
            if entities:
                current_action["entity_id"] = entities[0]

            _LOGGER.info(
                "Sunrise adjustment: '%s' timeslot start=%s "
                "(sunrise=%s, earliest=%s)",
                entity_id,
                target_time,
                sunrise_str,
                earliest_hhmm,
            )

            await self._hass.services.async_call(
                "scheduler",
                "edit",
                {
                    "entity_id": entity_id,
                    "timeslots": [{"start": target_time, "actions": [current_action]}],
                },
                blocking=False,
            )
