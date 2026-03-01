"""Coordinator for HomeShift integration."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODES,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCHEDULERS_PER_MODE,
    CONF_SCAN_INTERVAL,
    CONF_OVERRIDE_DURATION,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_DAY_MODES,
    DEFAULT_THERMOSTAT_MODE_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_OVERRIDE_DURATION,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_EVENT_MODE_MAP,
    DEFAULT_MODE_ABSENCE,
    KEY_EVENT_NONE,
    KEY_EVENT_VACATION,
    KEY_EVENT_TELEWORK,
    get_localized_defaults,
    EVENT_PERIOD_ALL_DAY,
    EVENT_PERIOD_MORNING,
    EVENT_PERIOD_AFTERNOON,
    THERMOSTAT_OFF_KEY,
)

_LOGGER = logging.getLogger(__name__)

# Midday threshold for determining morning vs afternoon half-days
MIDDAY_HOUR = 13


class HomeShiftCoordinator(DataUpdateCoordinator):
    """Class to manage fetching HomeShift data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        # Get configurable scan interval (in minutes)
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
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

        # Localized event type strings (e.g. "None"/"Aucun", "Vacation"/"Vacances", ...)
        _loc = get_localized_defaults(hass)
        self._event_none: str = _loc[KEY_EVENT_NONE]
        self._event_vacation: str = _loc[KEY_EVENT_VACATION]
        self._event_telework: str = _loc[KEY_EVENT_TELEWORK]

        self._day_mode: str = DEFAULT_DAY_MODES[0]
        self._current_event: str | None = None
        self._event_period: str | None = None  # all_day, morning, afternoon
        # Day-level event type: persists until midnight so the sensor doesn't
        # flicker back to EVENT_NONE between half-day events
        self._today_type: str = self._event_none
        self._today_date: date | None = None
        # Manual override duration (minutes) — mutable at runtime via number entity
        override_raw = entry.data.get(CONF_OVERRIDE_DURATION, DEFAULT_OVERRIDE_DURATION)
        try:
            self._override_duration_minutes: int = int(override_raw or 0)
        except (ValueError, TypeError):
            self._override_duration_minutes = DEFAULT_OVERRIDE_DURATION
        # Manual override: blocks auto-update until this datetime
        self._override_until: datetime | None = None

        # Parse day modes from config
        day_modes_str = entry.data.get(CONF_DAY_MODES, ", ".join(DEFAULT_DAY_MODES))
        self._day_modes = [mode.strip() for mode in day_modes_str.split(",")]

        # Parse thermostat mode map (InternalKey:DisplayValue, ...)
        thermostat_map_str = entry.data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP)
        self._thermostat_mode_map = self.parse_thermostat_mode_map(thermostat_map_str)
        self._thermostat_modes = list(self._thermostat_mode_map.values())
        self._thermostat_mode: str = self._thermostat_modes[0] if self._thermostat_modes else "Off"

        # Mode mapping configuration
        self._mode_default = entry.data.get(CONF_MODE_DEFAULT, DEFAULT_MODE_DEFAULT)
        self._mode_weekend = entry.data.get(CONF_MODE_WEEKEND, DEFAULT_MODE_WEEKEND)
        self._mode_holiday = entry.data.get(CONF_MODE_HOLIDAY, DEFAULT_MODE_HOLIDAY)
        self._event_mode_map = self.parse_event_mode_map(entry.data.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP))
        self._mode_absence = entry.data.get(CONF_MODE_ABSENCE, DEFAULT_MODE_ABSENCE)

        _LOGGER.info(
            "HomeShift coordinator initialized — "
            "calendar=%s, holiday_calendar=%s, scan_interval=%s min | "
            "day_modes=%s | "
            "mode_default=%s, mode_weekend=%s, mode_holiday=%s, mode_absence=%s | "
            "thermostat_modes=%s | event_mode_map=%s",
            entry.data.get(CONF_CALENDAR_ENTITY),
            entry.data.get(CONF_HOLIDAY_CALENDAR, "(missing)"),
            scan_interval,
            self._day_modes,
            self._mode_default,
            self._mode_weekend,
            self._mode_holiday,
            self._mode_absence,
            self._thermostat_modes,
            self._event_mode_map,
        )

    @staticmethod
    def parse_event_mode_map(raw: str) -> dict[str, str]:
        """Parse 'Event1:Mode1, Event2:Mode2' into a dict.

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
    def day_modes(self) -> list[str]:
        """Return configured day modes."""
        return self._day_modes

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
    def event_period(self) -> str | None:
        """Return current event period (all_day, morning, afternoon)."""
        return self._event_period

    @property
    def override_duration_minutes(self) -> int:
        """Return the current override duration in minutes (0 = disabled)."""
        return self._override_duration_minutes

    @property
    def override_until(self) -> datetime | None:
        """Return the datetime when the manual override expires, or None."""
        return self._override_until

    def set_override_duration_minutes(self, minutes: int) -> None:
        """Update the override duration (called by the number entity)."""
        self._override_duration_minutes = max(0, int(minutes))
        _LOGGER.info(
            "Override duration updated: %d min",
            self._override_duration_minutes,
        )

    async def async_set_day_mode(self, mode: str) -> None:
        """Set day mode manually (from UI select or service call)."""
        if mode not in self._day_modes:
            _LOGGER.warning(
                "Manual change ignored: day_mode '%s' is not in configured modes %s",
                mode,
                self._day_modes,
            )
            return
        old_mode = self._day_mode
        self._day_mode = mode
        # Activate override to block automatic changes for the configured duration
        override_minutes = self._override_duration_minutes
        if override_minutes > 0:
            self._override_until = dt_util.now() + timedelta(minutes=override_minutes)
            _LOGGER.info(
                "Manual change: day_mode '%s' -> '%s' | override active for %d min (until %s)",
                old_mode,
                mode,
                override_minutes,
                self._override_until.strftime("%H:%M:%S"),
            )
        else:
            self._override_until = None
            _LOGGER.info("Manual change: day_mode '%s' -> '%s'", old_mode, mode)
        await self.async_refresh_schedulers()
        # Rebuild and broadcast the full data dict so downstream sensors pick up
        # the new day_mode and override_until immediately (rather than stale data).
        self.async_set_updated_data(self._build_result())

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
                "Manual change ignored: thermostat_mode '%s' does not match any " "configured display value or internal key. " "Configured modes: %s | keys: %s",
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

    @staticmethod
    def detect_event_period(start_time_str: str, end_time_str: str) -> str:
        """Detect whether the event is all-day, morning, or afternoon.

        All-day events have times at midnight boundaries (00:00:00).
        Timed events are classified as:
          - morning: ends at or before MIDDAY_HOUR (13:00)
          - afternoon: starts at or after MIDDAY_HOUR (13:00)
          - all_day: spans both morning and afternoon
        """
        try:
            start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return EVENT_PERIOD_ALL_DAY

        # All-day events: both start and end at midnight
        if start_dt.hour == 0 and start_dt.minute == 0 and end_dt.hour == 0 and end_dt.minute == 0:
            return EVENT_PERIOD_ALL_DAY

        # Timed events: classify by time range
        if end_dt.hour <= MIDDAY_HOUR and end_dt.minute == 0:
            return EVENT_PERIOD_MORNING
        if start_dt.hour >= MIDDAY_HOUR:
            return EVENT_PERIOD_AFTERNOON

        # Spans entire day or both halves
        return EVENT_PERIOD_ALL_DAY

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
        calendar_entity = self.entry.data.get(CONF_CALENDAR_ENTITY)
        _LOGGER.debug(
            "Calendar sync started at %s (entity=%s, current mode=%s)",
            now.strftime("%Y-%m-%d %H:%M:%S"),
            calendar_entity,
            self._day_mode,
        )

        if not calendar_entity:
            _LOGGER.warning("No calendar entity configured, skipping sync")
            return self._build_result()

        # Get calendar state
        calendar_state = self.hass.states.get(calendar_entity)
        if not calendar_state:
            _LOGGER.warning("Calendar entity '%s' not found in Home Assistant states", calendar_entity)
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
        self._event_period = None
        today_type = self._event_none

        # Reset day-level event type at midnight (new calendar day)
        today = now.date()
        if today != self._today_date:
            _LOGGER.debug("New calendar day (%s), resetting today_type", today)
            self._today_type = self._event_none
            self._today_date = today

        if calendar_state.state == "on":
            event_message = calendar_state.attributes.get("message", "")
            event_start = calendar_state.attributes.get("start_time", "")
            event_end = calendar_state.attributes.get("end_time", "")

            if event_message:
                self._current_event = event_message
                self._event_period = self.detect_event_period(event_start, event_end)

                if self._event_vacation.lower() in event_message.lower():
                    today_type = self._event_vacation
                elif self._event_telework.lower() in event_message.lower():
                    today_type = self._event_telework
                else:
                    today_type = event_message
                # Persist the day-level type: once a known event is seen
                # for today it stays visible until midnight
                if today_type != self._event_none:
                    self._today_type = today_type

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
                    "Auto mode change: day_mode '%s' -> '%s' (event=%s, period=%s)",
                    self._day_mode,
                    new_mode,
                    self._current_event,
                    self._event_period,
                )
                self._day_mode = new_mode
                await self.async_refresh_schedulers()
            else:
                _LOGGER.debug(
                    "Periodic check: day_mode unchanged ('%s') | event=%s, period=%s",
                    self._day_mode,
                    self._current_event,
                    self._event_period,
                )

        return self._build_result()

    def _build_result(self) -> dict:
        """Build the data dict returned by the coordinator."""
        return {
            "today_type": self._today_type,
            "current_event": self._current_event,
            "event_period": self._event_period,
            "day_mode": self._day_mode,
            "thermostat_mode": self._thermostat_mode,
            "thermostat_mode_key": self.thermostat_mode_key,
            "override_until": self._override_until.isoformat() if self._override_until else None,
        }

    async def _determine_mode(self, today_type: str) -> str | None:
        """Determine the appropriate mode based on current state.

        Uses configurable mappings instead of hardcoded values.
        Priority:
        1. Active calendar event matching event_mode_map -> mapped mode
        2. Weekend -> mode_weekend
        3. Holiday calendar active -> mode_holiday
        4. Default -> mode_default
        """
        now = dt_util.now()
        is_weekend = now.weekday() in [5, 6]

        # Check holiday calendar
        holiday_calendar = self.entry.data.get(CONF_HOLIDAY_CALENDAR, "")
        is_holiday = False
        holiday_state = self.hass.states.get(holiday_calendar)
        if holiday_state and holiday_state.state == "on":
            is_holiday = True

        # 1. Check event_mode_map for the current event type
        if today_type and today_type != self._event_none:
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

    async def async_check_next_day(self) -> None:
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
        schedulers_per_mode: dict[str, list[str]] = self.entry.data.get(
            CONF_SCHEDULERS_PER_MODE, {}
        )

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
