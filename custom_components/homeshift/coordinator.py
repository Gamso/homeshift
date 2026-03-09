"""Coordinator for HomeShift integration."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODE_MAP,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCHEDULERS_PER_MODE,
    CONF_SCAN_INTERVAL,
    CONF_OVERRIDE_DURATION,
    CONF_EARLY_SWITCH_MINUTES,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_DAY_MODE_MAP,
    DEFAULT_THERMOSTAT_MODE_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_OVERRIDE_DURATION,
    DEFAULT_EARLY_SWITCH_MINUTES,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_EVENT_MODE_MAP,
    DEFAULT_MODE_ABSENCE,
    EVENT_NONE,
    THERMOSTAT_OFF_KEY,
    get_localized_defaults,
)

_LOGGER = logging.getLogger(__name__)

# Midday threshold for determining morning vs afternoon half-days
MIDDAY_HOUR = 13

# Persistent storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{__name__}.state"


def _parse_event_dt(start_str: str, fallback_tzinfo: Any) -> datetime | None:
    """Parse an ISO datetime string (from calendar.get_events) into a datetime.

    Handles timezone-aware strings like '2026-03-07T14:00:00+01:00',
    naive strings like '2026-03-07T14:00:00', and date-only '2026-03-07'.
    When the parsed value is naive and fallback_tzinfo is provided, it is applied.
    Returns None for unparseable values.
    """
    if not start_str:
        return None
    try:
        dt = datetime.fromisoformat(str(start_str))
        if dt.tzinfo is None and fallback_tzinfo is not None:
            dt = dt.replace(tzinfo=fallback_tzinfo)
        return dt
    except (ValueError, TypeError):
        return None


class HomeShiftCoordinator(DataUpdateCoordinator):
    """Class to manage fetching HomeShift data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        # Merge config_entry.data with config_entry.options so that values saved
        # via the options flow (stored in entry.options) take precedence.
        _config = {**entry.data, **entry.options}
        # Localized defaults — used as fallback when a key is absent from the entry
        _loc = get_localized_defaults(hass)

        # Get configurable scan interval (in minutes)
        scan_interval = _config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        try:
            scan_interval = int(scan_interval)
        except (ValueError, TypeError):
            scan_interval = DEFAULT_SCAN_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
        )
        self.entry = entry

        # Parse day mode map (InternalKey:DisplayValue, ...) — same pattern as thermostat
        day_map_str = _config.get(CONF_DAY_MODE_MAP, _loc.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
        self._day_mode_map: dict[str, str] = self.parse_day_mode_map(day_map_str)
        self._day_modes: list[str] = list(self._day_mode_map.values())
        self._day_mode: str = self._day_modes[0] if self._day_modes else "Home"

        self._current_event: str | None = None
        # Day-level event type: persists until midnight so the sensor doesn't
        # flicker back to EVENT_NONE between half-day events.
        # Stored as the matched event keyword (locale-independent) or EVENT_NONE.
        self._today_type: str = EVENT_NONE
        self._today_date: date | None = None
        # Manual override duration (minutes) — mutable at runtime via number entity
        override_raw = _config.get(CONF_OVERRIDE_DURATION, DEFAULT_OVERRIDE_DURATION)
        try:
            self._override_duration_minutes: int = int(override_raw or 0)
        except (ValueError, TypeError):
            self._override_duration_minutes = DEFAULT_OVERRIDE_DURATION
        # Early switch: number of minutes to pre-activate a timed event before its start
        early_raw = _config.get(CONF_EARLY_SWITCH_MINUTES, DEFAULT_EARLY_SWITCH_MINUTES)
        try:
            self._early_switch_minutes: int = int(early_raw or 0)
        except (ValueError, TypeError):
            self._early_switch_minutes = DEFAULT_EARLY_SWITCH_MINUTES
        # Manual override: blocks auto-update until this datetime
        self._override_until: datetime | None = None
        # Predicted next automatic mode change
        self._next_mode: str | None = None
        self._next_mode_at: datetime | None = None

        # Parse thermostat mode map (InternalKey:DisplayValue, ...)
        thermostat_map_str = _config.get(CONF_THERMOSTAT_MODE_MAP, _loc.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))
        self._thermostat_mode_map = self.parse_thermostat_mode_map(thermostat_map_str)
        self._thermostat_modes = list(self._thermostat_mode_map.values())
        self._thermostat_mode: str = self._thermostat_modes[0] if self._thermostat_modes else "Off"

        # Mode mapping configuration — values are day mode keys, resolved to display names
        _mode_default_key = _config.get(CONF_MODE_DEFAULT, _loc.get(CONF_MODE_DEFAULT, DEFAULT_MODE_DEFAULT))
        _mode_weekend_key = _config.get(CONF_MODE_WEEKEND, _loc.get(CONF_MODE_WEEKEND, DEFAULT_MODE_WEEKEND))
        _mode_holiday_key = _config.get(CONF_MODE_HOLIDAY, _loc.get(CONF_MODE_HOLIDAY, DEFAULT_MODE_HOLIDAY))
        _mode_absence_key = _config.get(CONF_MODE_ABSENCE, _loc.get(CONF_MODE_ABSENCE, DEFAULT_MODE_ABSENCE))
        self._mode_default = self._day_mode_map.get(_mode_default_key, _mode_default_key)
        self._mode_weekend = self._day_mode_map.get(_mode_weekend_key, _mode_weekend_key)
        self._mode_holiday = self._day_mode_map.get(_mode_holiday_key, _mode_holiday_key)
        self._mode_absence = self._day_mode_map.get(_mode_absence_key, _mode_absence_key)
        # event_mode_map: event keyword (lowercase) → day mode display name
        raw_event_map = self.parse_event_mode_map(_config.get(CONF_EVENT_MODE_MAP, _loc.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP)))
        # Values in raw_event_map are keys (e.g. "home", "remote") — resolve to display
        self._event_mode_map: dict[str, str] = {kw: self._day_mode_map.get(mode_key, mode_key) for kw, mode_key in raw_event_map.items()}

        _LOGGER.info(
            "HomeShift coordinator initialized — "
            "calendar=%s, holiday_calendar=%s, scan_interval=%s min | "
            "day_mode_map=%s | "
            "mode_default=%s, mode_weekend=%s, mode_holiday=%s, mode_absence=%s | "
            "thermostat_modes=%s | event_mode_map=%s",
            _config.get(CONF_CALENDAR_ENTITY),
            _config.get(CONF_HOLIDAY_CALENDAR, "(missing)"),
            scan_interval,
            self._day_mode_map,
            self._mode_default,
            self._mode_weekend,
            self._mode_holiday,
            self._mode_absence,
            self._thermostat_modes,
            self._event_mode_map,
        )

        # Persistent storage — used to restore modes after HA restart
        self._store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")

    @property
    def _config(self) -> dict:
        """Return merged config: entry.data overridden by entry.options."""
        return {**self.entry.data, **self.entry.options}

    async def async_restore_state(self) -> None:
        """Restore persisted day_mode and thermostat_mode from storage.

        Called once during setup, before the first coordinator refresh, so that
        the coordinator starts with the last-known modes instead of the defaults.
        """
        try:
            stored = await self._store.async_load()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not load persisted state: %s", err)
            return

        if not stored:
            _LOGGER.debug("No persisted state found, using configured defaults")
            return

        day_mode_key = stored.get("day_mode_key")
        if day_mode_key and day_mode_key in self._day_mode_map:
            resolved = self._day_mode_map[day_mode_key]
            _LOGGER.info(
                "Restoring persisted day_mode: key=%s -> '%s'", day_mode_key, resolved
            )
            self._day_mode = resolved

        thermostat_mode_key = stored.get("thermostat_mode_key")
        if thermostat_mode_key and thermostat_mode_key in self._thermostat_mode_map:
            resolved = self._thermostat_mode_map[thermostat_mode_key]
            _LOGGER.info(
                "Restoring persisted thermostat_mode: key=%s -> '%s'",
                thermostat_mode_key,
                resolved,
            )
            self._thermostat_mode = resolved

    async def _async_save_state(self) -> None:
        """Persist current day_mode_key and thermostat_mode_key to storage."""
        try:
            await self._store.async_save(
                {
                    "day_mode_key": self.day_mode_key,
                    "thermostat_mode_key": self.thermostat_mode_key,
                }
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not persist coordinator state: %s", err)

    @staticmethod
    def parse_day_mode_map(raw: str) -> dict[str, str]:
        """Parse 'Key1:Display1, Key2:Display2' into an ordered dict.

        Keys are internal English identifiers; values are display texts.
        Identical to parse_thermostat_mode_map — kept as a named alias for clarity.
        """
        mapping: dict[str, str] = {}
        if not raw:
            return mapping
        for pair in raw.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            key, display = pair.split(":", 1)
            key = key.strip()
            display = display.strip()
            if key and display:
                mapping[key] = display
        return mapping

    @staticmethod
    def parse_event_mode_map(raw: str) -> dict[str, str]:
        """Parse 'Event1:ModeKey1, Event2:ModeKey2' into a dict.

        Returns a case-insensitive-lookup dict (keys are lowered).
        """
        mapping: dict[str, str] = {}
        if not raw:
            return mapping
        for pair in raw.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            event_key, mode_value = pair.split(":", 1)
            event_key = event_key.strip()
            mode_value = mode_value.strip()
            if event_key and mode_value:
                mapping[event_key.lower()] = mode_value
        return mapping

    @staticmethod
    def parse_thermostat_mode_map(raw: str) -> dict[str, str]:
        """Parse 'Key1:Display1, Key2:Display2' into an ordered dict.

        Keys are internal English identifiers (case preserved).
        Values are display texts used in UI and as scheduler tags.
        """
        mapping: dict[str, str] = {}
        if not raw:
            return mapping
        for pair in raw.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            key, display = pair.split(":", 1)
            key = key.strip()
            display = display.strip()
            if key and display:
                mapping[key] = display
        return mapping

    @property
    def day_mode_map(self) -> dict[str, str]:
        """Return the full day mode map (internal_key -> display_value)."""
        return self._day_mode_map

    @property
    def day_modes(self) -> list[str]:
        """Return configured day mode display values."""
        return self._day_modes

    @property
    def day_mode_key(self) -> str | None:
        """Return the internal key (e.g. 'Work', 'Remote') for the current day mode."""
        for key, display in self._day_mode_map.items():
            if display == self._day_mode:
                return key
        return None

    @property
    def thermostat_modes(self) -> list[str]:
        """Return configured thermostat mode display values."""
        return self._thermostat_modes

    @property
    def thermostat_mode_map(self) -> dict[str, str]:
        """Return the full thermostat mode map (internal_key -> display_value)."""
        return self._thermostat_mode_map

    @property
    def day_mode(self) -> str:
        """Return current day mode."""
        return self._day_mode

    @day_mode.setter
    def day_mode(self, value: str) -> None:
        """Set day mode directly (no override logic or scheduler refresh).

        Intended for test setup only. Use async_set_day_mode() at runtime.
        """
        self._day_mode = value

    @property
    def thermostat_mode(self) -> str:
        """Return current thermostat mode."""
        return self._thermostat_mode

    @property
    def current_event(self) -> str | None:
        """Return current calendar event type."""
        return self._current_event

    @property
    def override_duration_minutes(self) -> int:
        """Return the current override duration in minutes (0 = disabled)."""
        return self._override_duration_minutes

    @property
    def override_until(self) -> datetime | None:
        """Return the datetime when the manual override expires, or None."""
        return self._override_until

    @property
    def next_mode_predicted(self) -> str | None:
        """Predicted day mode at the next automatic change."""
        return self._next_mode

    @property
    def next_mode_at(self) -> datetime | None:
        """Timestamp when the next automatic day mode change is expected."""
        return self._next_mode_at

    def set_override_duration_minutes(self, minutes: int) -> None:
        """Update the override duration (called by the number entity)."""
        self._override_duration_minutes = max(0, int(minutes))
        _LOGGER.info(
            "Override duration updated: %d min",
            self._override_duration_minutes,
        )

    @property
    def early_switch_minutes(self) -> int:
        """Return the early switch advance time in minutes (0 = disabled)."""
        return self._early_switch_minutes

    def set_early_switch_minutes(self, minutes: int) -> None:
        """Update the early switch duration (called by the number entity)."""
        self._early_switch_minutes = max(0, int(minutes))
        _LOGGER.info(
            "Early switch duration updated: %d min",
            self._early_switch_minutes,
        )

    def _resolve_day_mode_display(self, mode: str) -> str | None:
        """Resolve a day mode value to its display string.

        Accepts either:
        - A display value (e.g. 'Télétravail') — returned as-is.
        - An internal key (e.g. 'remote', 'Remote') — resolved to its display value.

        Returns None if no match is found.
        """
        if mode in self._day_modes:
            return mode
        mode_lower = mode.lower()
        for key, display in self._day_mode_map.items():
            if key.lower() == mode_lower:
                return display
        return None

    async def async_set_day_mode(self, mode: str) -> None:
        """Set day mode manually (from UI select or service call).

        Accepts both the display value (language-specific, e.g. 'Télétravail') and
        the internal key (language-independent, e.g. 'remote' or 'Remote').
        """
        resolved = self._resolve_day_mode_display(mode)
        if resolved is None:
            _LOGGER.warning(
                "Manual change ignored: day_mode '%s' does not match any" " configured display value or internal key." " Configured modes: %s | keys: %s",
                mode,
                self._day_modes,
                list(self._day_mode_map.keys()),
            )
            return
        old_mode = self._day_mode
        self._day_mode = resolved
        # Activate override to block automatic changes for the configured duration
        override_minutes = self._override_duration_minutes
        if override_minutes > 0:
            self._override_until = dt_util.now() + timedelta(minutes=override_minutes)
            _LOGGER.info(
                "Manual change: day_mode '%s' -> '%s' (key=%s) | override active for %d min (until %s)",
                old_mode,
                resolved,
                self.day_mode_key,
                override_minutes,
                self._override_until.strftime("%H:%M:%S"),
            )
        else:
            self._override_until = None
            _LOGGER.info("Manual change: day_mode '%s' -> '%s' (key=%s)", old_mode, resolved, self.day_mode_key)
        await self.async_refresh_schedulers()
        # Rebuild and broadcast the full data dict so downstream sensors pick up
        # the new day_mode and override_until immediately (rather than stale data).
        self.async_set_updated_data(self._build_result())
        await self._async_save_state()

    @property
    def thermostat_mode_key(self) -> str | None:
        """Return the internal key (e.g. 'Off', 'Heating') for the current thermostat mode.

        This is the language-independent identifier used for automation and
        service calls regardless of the configured display language.
        """
        for key, display in self._thermostat_mode_map.items():
            if display == self._thermostat_mode:
                return key
        return None

    def _resolve_thermostat_display(self, mode: str) -> str | None:
        """Resolve a thermostat mode value to its display string.

        Accepts either:
        - A display value (e.g. 'Chauffage') — returned as-is.
        - An internal key (e.g. 'heating', 'Heating') — resolved to its display value.

        Returns None if no match is found.
        """
        if mode in self._thermostat_modes:
            return mode
        mode_lower = mode.lower()
        for key, display in self._thermostat_mode_map.items():
            if key.lower() == mode_lower:
                return display
        return None

    async def async_set_thermostat_mode(self, mode: str) -> None:
        """Set thermostat mode manually (from UI select or service call).

        Accepts both the display value (language-specific, e.g. 'Chauffage') and
        the internal key (language-independent, e.g. 'heating' or 'Heating').
        """
        resolved = self._resolve_thermostat_display(mode)
        if resolved is None:
            _LOGGER.warning(
                "Manual change ignored: thermostat_mode '%s' does not match any" " configured display value or internal key." " Configured modes: %s | keys: %s",
                mode,
                self._thermostat_modes,
                list(self._thermostat_mode_map.keys()),
            )
            return
        old_mode = self._thermostat_mode
        self._thermostat_mode = resolved
        _LOGGER.info(
            "Manual change: thermostat_mode '%s' -> '%s' (key=%s)",
            old_mode,
            resolved,
            self.thermostat_mode_key,
        )
        await self.async_refresh_schedulers()
        self.async_set_updated_data(self._build_result())
        await self._async_save_state()

    async def async_update_data(self) -> dict:
        """Public entry point for fetching data (delegates to _async_update_data).

        Exposed so that tests can call this without accessing a protected member.
        """
        return await self._async_update_data()

    async def _async_update_data(self) -> dict:
        """Fetch data from calendar and determine current mode.

        This runs periodically based on scan_interval. It checks the current
        calendar state and auto-updates day_mode unless mode is absence.
        This handles half-day events naturally: a timed calendar event is only
        active during its time window.
        """
        now = dt_util.now()
        calendar_entity = self._config.get(CONF_CALENDAR_ENTITY)
        _LOGGER.debug(
            "Calendar sync started at %s (entity=%s, current mode=%s)",
            now.strftime("%Y-%m-%d %H:%M:%S"),
            calendar_entity,
            self._day_mode,
        )

        if not calendar_entity:
            _LOGGER.warning("No calendar entity configured, skipping sync")
            self._next_mode, self._next_mode_at = None, None
            return self._build_result()

        # Get calendar state
        calendar_state = self.hass.states.get(calendar_entity)
        if not calendar_state:
            _LOGGER.warning("Calendar entity '%s' not found in Home Assistant states", calendar_entity)
            self._next_mode, self._next_mode_at = None, None
            return self._build_result()

        _LOGGER.debug(
            "Calendar '%s' -> state=%s | event='%s' | start=%s end=%s",
            calendar_entity,
            calendar_state.state,
            calendar_state.attributes.get("message", ""),
            calendar_state.attributes.get("start_time", ""),
            calendar_state.attributes.get("end_time", ""),
        )

        # Determine current event from calendar
        self._current_event = None
        today_type = EVENT_NONE

        # Reset day-level event type at midnight (new calendar day)
        today = now.date()
        if today != self._today_date:
            _LOGGER.debug("New calendar day (%s), resetting today_type", today)
            self._today_type = EVENT_NONE
            self._today_date = today

        if calendar_state.state == "on":
            event_message = calendar_state.attributes.get("message", "")
            event_start = calendar_state.attributes.get("start_time", "")
            event_end = calendar_state.attributes.get("end_time", "")

            if event_message:
                self._current_event = event_message

                # Match event message against configured event keywords (case-insensitive)
                matched_keyword: str | None = None
                for kw in self._event_mode_map:
                    if kw in event_message.lower():
                        matched_keyword = kw
                        break
                today_type = matched_keyword if matched_keyword is not None else event_message
                # Persist the day-level type once a known event is seen for today
                if today_type != EVENT_NONE:
                    self._today_type = today_type

        # Early switch: if calendar is currently off and early_switch_minutes > 0, check
        # if a timed (non-all-day) event starts within the early window.
        if calendar_state.state != "on" and self._early_switch_minutes > 0:
            early_end = now + timedelta(minutes=self._early_switch_minutes)
            early_events = await self._async_get_upcoming_events(calendar_entity, now, early_end)
            now_naive = self._to_naive(now)
            early_end_naive = self._to_naive(early_end)
            for event in early_events:
                if self._is_all_day_event(event):
                    continue
                start_dt = _parse_event_dt(event.get("start", ""), now.tzinfo)
                if start_dt is None:
                    continue
                start_naive = self._to_naive(start_dt)
                # Only pre-activate events that actually start within (now, early_end]
                if not now_naive < start_naive <= early_end_naive:
                    continue
                summary = event.get("summary", "")
                for kw in self._event_mode_map:
                    if kw in summary.lower():
                        today_type = kw
                        break
                if today_type != EVENT_NONE:
                    _LOGGER.debug(
                        "Early switch: pre-activating event '%s' (starts within %d min)",
                        summary,
                        self._early_switch_minutes,
                    )
                    break

        # Auto-update mode (skip if absence mode or manual override is active)
        if self._day_mode == self._mode_absence:
            _LOGGER.debug(
                "Periodic check: auto-update skipped, absence mode active ('%s')",
                self._day_mode,
            )
        elif self._override_until is not None and now < self._override_until:
            remaining = int((self._override_until - now).total_seconds() / 60) + 1
            _LOGGER.debug(
                "Periodic check: auto-update skipped, manual override active for ~%d more min",
                remaining,
            )
        else:
            if self._override_until is not None:
                _LOGGER.info(
                    "Manual override expired at %s, resuming automatic mode changes",
                    self._override_until.strftime("%H:%M:%S"),
                )
                self._override_until = None
            new_mode = await self._determine_mode(today_type)
            if new_mode and new_mode != self._day_mode and new_mode in self._day_modes:
                _LOGGER.info(
                    "Auto mode change: day_mode '%s' -> '%s' (event=%s)",
                    self._day_mode,
                    new_mode,
                    self._current_event,
                )
                self._day_mode = new_mode
                await self.async_refresh_schedulers()
                await self._async_save_state()
            else:
                _LOGGER.debug(
                    "Periodic check: day_mode unchanged ('%s') | event=%s",
                    self._day_mode,
                    self._current_event,
                )

        # Compute when and to what mode the next automatic change is expected
        self._next_mode, self._next_mode_at = await self._compute_next_mode_change(calendar_state, now)

        return self._build_result()

    def _build_result(self) -> dict:
        """Build the data dict returned by the coordinator."""
        return {
            "today_type": self._today_type,
            "current_event": self._current_event,
            "day_mode": self._day_mode,
            "day_mode_key": self.day_mode_key,
            "thermostat_mode": self._thermostat_mode,
            "thermostat_mode_key": self.thermostat_mode_key,
            "override_until": self._override_until.isoformat() if self._override_until else None,
            "next_mode_predicted": self._next_mode,
            "next_mode_at": self._next_mode_at.isoformat() if self._next_mode_at else None,
        }

    async def _async_get_upcoming_events(self, calendar_entity: str, start: datetime, end: datetime) -> list[dict]:
        """Fetch calendar events in [start, end] via the calendar.get_events service.

        Returns a list of event dicts (keys include 'start', 'end', 'summary').
        Returns an empty list if the service is unavailable or the call fails.
        """
        try:
            result = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": calendar_entity,
                    "start_date_time": start.isoformat(),
                    "end_date_time": end.isoformat(),
                },
                blocking=True,
                return_response=True,
            )
            entity_data = result.get(calendar_entity) if isinstance(result, dict) else None
            if isinstance(entity_data, dict):
                events = entity_data.get("events", [])
                if isinstance(events, list):
                    return [e for e in events if isinstance(e, dict)]
        except Exception:  # noqa: BLE001
            pass
        return []

    @staticmethod
    def _is_all_day_event(event: dict) -> bool:
        """Return True if the event from calendar.get_events is an all-day event.

        All-day events have a date-only 'start' value (no 'T' time separator).
        """
        return "T" not in str(event.get("start", ""))

    @staticmethod
    def _to_naive(dt: datetime) -> datetime:
        """Strip tzinfo for mixed-timezone-safe comparisons."""
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

    async def _mode_at_time(
        self,
        at: datetime,
        upcoming_events: list[dict],
        active_calendar_state,
        ref_tzinfo,
    ) -> str | None:
        """Determine what day mode would be active at `at`.

        Checks (in priority order):
        1. Upcoming events (from get_events) that are active at `at`
        2. Currently active calendar event (from calendar_state) if it still covers `at`
        3. Weekend / holiday / default fallback
        """
        at_naive = self._to_naive(at)

        # 1. Scan events returned by get_events
        for event in upcoming_events:
            start_dt = _parse_event_dt(event.get("start", ""), ref_tzinfo)
            end_dt = _parse_event_dt(event.get("end", ""), ref_tzinfo)
            if start_dt is None or end_dt is None:
                continue
            if self._to_naive(start_dt) <= at_naive < self._to_naive(end_dt):
                summary = event.get("summary", "")
                for kw, mode in self._event_mode_map.items():
                    if kw in summary.lower():
                        return mode

        # 2. Currently active event (may not appear in upcoming_events when
        #    get_events returns only future starts)
        if active_calendar_state is not None and active_calendar_state.state == "on":
            start_str = active_calendar_state.attributes.get("start_time", "")
            end_str = active_calendar_state.attributes.get("end_time", "")
            try:
                s = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                e = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                if s <= at_naive < e:
                    message = active_calendar_state.attributes.get("message", "")
                    for kw, mode in self._event_mode_map.items():
                        if kw in message.lower():
                            return mode
            except (ValueError, TypeError):
                pass

        # 3. Early switch — timed event starts within early_switch_minutes after `at`
        if self._early_switch_minutes > 0:
            early_delta = timedelta(minutes=self._early_switch_minutes)
            for event in upcoming_events:
                if self._is_all_day_event(event):
                    continue
                start_dt = _parse_event_dt(event.get("start", ""), ref_tzinfo)
                if start_dt is None:
                    continue
                start_naive = self._to_naive(start_dt)
                if start_naive - early_delta <= at_naive < start_naive:
                    summary = event.get("summary", "")
                    for kw, mode in self._event_mode_map.items():
                        if kw in summary.lower():
                            return mode

        # 4. No active mapped event → weekend / holiday / default
        return await self._determine_mode(EVENT_NONE, at_time=at)

    async def _compute_next_mode_change(self, calendar_state, now: datetime) -> tuple[str | None, datetime | None]:
        """Estimate the next automatic day-mode change: (predicted_mode, when).

        General algorithm — handles any number of events per day:
        1. Fetch all events over the next 2 days via calendar.get_events.
        2. Build inflection points: every event start/end + midnight boundaries.
        3. For each inflection point (chronological), compute the active mode.
        4. Return the first point where the mode differs from the current mode.
        """
        calendar_entity = self._config.get(CONF_CALENDAR_ENTITY, "")
        now_naive = self._to_naive(now)

        # Fetch events for today + tomorrow (2-day window)
        end_window = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        upcoming = await self._async_get_upcoming_events(calendar_entity, now, end_window)

        # Collect candidate inflection points (all strictly after now)
        candidates: set[datetime] = set()

        # Midnight boundaries: tonight and tomorrow night
        for d in range(1, 3):
            midnight = (now + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
            candidates.add(midnight)

        # End of the currently active event (calendar_state uses "YYYY-MM-DD HH:MM:SS" format)
        if calendar_state is not None and calendar_state.state == "on":
            end_str = calendar_state.attributes.get("end_time", "")
            try:
                end_naive = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                if end_naive > now_naive:
                    candidates.add(end_naive.replace(tzinfo=now.tzinfo))
            except (ValueError, TypeError):
                pass

        # Start and end of every upcoming event from get_events (ISO format)
        for event in upcoming:
            for time_key in ("start", "end"):
                dt = _parse_event_dt(event.get(time_key, ""), now.tzinfo)
                if dt is not None and self._to_naive(dt) > now_naive:
                    candidates.add(dt)

        # Early switch: for timed events add event_start - early_switch_minutes as candidate
        if self._early_switch_minutes > 0:
            early_delta = timedelta(minutes=self._early_switch_minutes)
            for event in upcoming:
                if self._is_all_day_event(event):
                    continue
                start_dt = _parse_event_dt(event.get("start", ""), now.tzinfo)
                if start_dt is not None:
                    early_dt = start_dt - early_delta
                    if self._to_naive(early_dt) > now_naive:
                        candidates.add(early_dt)

        # Sort chronologically using naive times to avoid tz comparison errors
        sorted_candidates = sorted(candidates, key=self._to_naive)

        # Walk candidates and return the first that produces a different mode
        current_mode = self._day_mode
        for candidate in sorted_candidates:
            mode_at = await self._mode_at_time(candidate, upcoming, calendar_state, now.tzinfo)
            if mode_at != current_mode:
                return mode_at, candidate

        return None, None

    async def _determine_mode(self, today_type: str, at_time: datetime | None = None) -> str | None:
        """Determine the appropriate mode based on current state.

        Uses configurable mappings instead of hardcoded values.
        Priority:
        1. Active calendar event matching event_mode_map -> mapped display mode
        2. Weekend -> mode_weekend
        3. Holiday calendar active -> mode_holiday
        4. Default -> mode_default

        at_time: datetime to use for weekday check (defaults to now).
        Note: holiday calendar check always uses the current HA calendar state.
        """
        now = at_time if at_time is not None else dt_util.now()
        is_weekend = now.weekday() in [5, 6]

        # Check holiday calendar
        holiday_calendar = self._config.get(CONF_HOLIDAY_CALENDAR, "")
        is_holiday = False
        holiday_state = self.hass.states.get(holiday_calendar)
        if holiday_state and holiday_state.state == "on":
            is_holiday = True

        # 1. Check event_mode_map for the current event keyword
        if today_type and today_type != EVENT_NONE:
            mapped_mode = self._event_mode_map.get(today_type.lower())
            if mapped_mode:
                return mapped_mode

        # 2. Weekend
        if is_weekend:
            return self._mode_weekend

        # 3. Holiday
        if is_holiday:
            return self._mode_holiday

        # 4. Default (regular work day)
        return self._mode_default

    async def async_sync_calendar(self) -> None:
        """Check and set day type (called at daily check time and periodically).

        This is the daily check entry point. It triggers a full refresh which
        in turn calls _async_update_data and auto-determines the mode.
        """
        if self._day_mode == self._mode_absence:
            _LOGGER.info("Mode is %s, skipping automatic check", self._mode_absence)
            return

        _LOGGER.info("Running scheduled day type check")
        await self.async_refresh()

    async def async_refresh_schedulers(self) -> None:
        """Turn on scheduler switches for the active day mode, turn off all others.

        The configuration maps each day mode to a list of switch entity IDs
        (stored under CONF_SCHEDULERS_PER_MODE).  When the day mode changes we:
          1. Collect the switches that should be ON  (active mode).
          2. Collect the switches that should be OFF (every other mode),
             excluding any that are also in the active list.
          3. Fire the switch.turn_on / switch.turn_off service calls.
        """
        schedulers_per_mode: dict[str, list[str]] = self._config.get(CONF_SCHEDULERS_PER_MODE, {})

        if not schedulers_per_mode:
            _LOGGER.debug("No schedulers configured, skipping refresh")
            return

        _LOGGER.info(
            "Refreshing schedulers: day_mode=%s, thermostat_mode=%s",
            self._day_mode,
            self._thermostat_mode,
        )

        # Build activate / deactivate sets
        to_enable: set[str] = set(schedulers_per_mode.get(self._day_mode, []))
        to_disable: set[str] = set()
        for mode, switches in schedulers_per_mode.items():
            if mode != self._day_mode:
                for sw in switches:
                    if sw not in to_enable:  # never disable a shared switch
                        to_disable.add(sw)

        # When thermostat mode is Off, force-disable every scheduler that carries
        # a thermostat-mode tag (e.g. "Chauffage", "Climatisation", …).
        # Schedulers without any thermostat tag are left untouched.
        thermostat_key = self.thermostat_mode_key
        if thermostat_key == THERMOSTAT_OFF_KEY and self._thermostat_mode_map:
            thermostat_tags: set[str] = set(self._thermostat_mode_map.values())
            all_switches: set[str] = set()
            for swlist in schedulers_per_mode.values():
                all_switches.update(swlist)
            for entity_id in all_switches:
                state = self.hass.states.get(entity_id)
                if state is None:
                    continue
                entity_tags: list = state.attributes.get("tags", []) or []
                if set(entity_tags) & thermostat_tags:
                    _LOGGER.debug(
                        "Thermostat OFF: force-disabling scheduler '%s' (tags=%s)",
                        entity_id,
                        entity_tags,
                    )
                    to_disable.add(entity_id)
                    to_enable.discard(entity_id)

        # Turn off first so we don't have conflicting schedulers briefly active
        if to_disable:
            _LOGGER.debug("Turning OFF schedulers: %s", sorted(to_disable))
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": sorted(to_disable)},
                blocking=False,
            )

        if to_enable:
            _LOGGER.debug("Turning ON schedulers: %s", sorted(to_enable))
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": sorted(to_enable)},
                blocking=False,
            )
        elif self._day_mode and schedulers_per_mode.get(self._day_mode) is not None:
            _LOGGER.debug(
                "No schedulers assigned to day_mode '%s'", self._day_mode
            )
