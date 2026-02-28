"""Coordinator for Day Mode integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODES,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCAN_INTERVAL,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_DAY_MODES,
    DEFAULT_THERMOSTAT_MODE_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_EVENT_MODE_MAP,
    DEFAULT_MODE_ABSENCE,
    EVENT_NONE,
    EVENT_VACATION,
    EVENT_TELEWORK,
    EVENT_PERIOD_ALL_DAY,
    EVENT_PERIOD_MORNING,
    EVENT_PERIOD_AFTERNOON,
)

_LOGGER = logging.getLogger(__name__)

# Midday threshold for determining morning vs afternoon half-days
MIDDAY_HOUR = 13


class DayModeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Day Mode data."""

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
        self._day_mode: str = DEFAULT_DAY_MODES[0]
        self._current_event: str | None = None
        self._event_period: str | None = None  # all_day, morning, afternoon

        # Parse day modes from config
        day_modes_str = entry.data.get(CONF_DAY_MODES, ", ".join(DEFAULT_DAY_MODES))
        self._day_modes = [mode.strip() for mode in day_modes_str.split(",")]

        # Parse thermostat mode map (InternalKey:DisplayValue, ...)
        thermostat_map_str = entry.data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP)
        self._thermostat_mode_map = self._parse_thermostat_mode_map(thermostat_map_str)
        self._thermostat_modes = list(self._thermostat_mode_map.values())
        self._thermostat_mode: str = self._thermostat_modes[0] if self._thermostat_modes else "Off"

        # Mode mapping configuration
        self._mode_default = entry.data.get(CONF_MODE_DEFAULT, DEFAULT_MODE_DEFAULT)
        self._mode_weekend = entry.data.get(CONF_MODE_WEEKEND, DEFAULT_MODE_WEEKEND)
        self._mode_holiday = entry.data.get(CONF_MODE_HOLIDAY, DEFAULT_MODE_HOLIDAY)
        self._event_mode_map = self._parse_event_mode_map(entry.data.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP))
        self._mode_absence = entry.data.get(CONF_MODE_ABSENCE, DEFAULT_MODE_ABSENCE)

        _LOGGER.info(
            "Day Mode coordinator initialized — "
            "calendar=%s, holiday_calendar=%s, scan_interval=%s min | "
            "day_modes=%s | "
            "mode_default=%s, mode_weekend=%s, mode_holiday=%s, mode_absence=%s | "
            "thermostat_modes=%s | event_mode_map=%s",
            entry.data.get(CONF_CALENDAR_ENTITY),
            entry.data.get(CONF_HOLIDAY_CALENDAR) or "(none)",
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
    def _parse_event_mode_map(raw: str) -> dict[str, str]:
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
    def _parse_thermostat_mode_map(raw: str) -> dict[str, str]:
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
        _LOGGER.info("Manual change: day_mode '%s' -> '%s'", old_mode, mode)
        await self.async_refresh_schedulers()
        self.async_set_updated_data(self.data)

    async def async_set_thermostat_mode(self, mode: str) -> None:
        """Set thermostat mode manually (from UI select or service call)."""
        if mode not in self._thermostat_modes:
            _LOGGER.warning(
                "Manual change ignored: thermostat_mode '%s' is not in configured modes %s",
                mode,
                self._thermostat_modes,
            )
            return
        old_mode = self._thermostat_mode
        self._thermostat_mode = mode
        _LOGGER.info("Manual change: thermostat_mode '%s' -> '%s'", old_mode, mode)

    @staticmethod
    def _detect_event_period(start_time_str: str, end_time_str: str) -> str:
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
            return self._build_result(next_day_type=EVENT_NONE)

        # Get calendar state
        calendar_state = self.hass.states.get(calendar_entity)
        if not calendar_state:
            _LOGGER.warning("Calendar entity '%s' not found in Home Assistant states", calendar_entity)
            return self._build_result(next_day_type=EVENT_NONE)

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
        next_day_type = EVENT_NONE

        if calendar_state.state == "on":
            event_message = calendar_state.attributes.get("message", "")
            event_start = calendar_state.attributes.get("start_time", "")
            event_end = calendar_state.attributes.get("end_time", "")

            if event_message:
                self._current_event = event_message
                self._event_period = self._detect_event_period(event_start, event_end)

                if EVENT_VACATION.lower() in event_message.lower():
                    next_day_type = EVENT_VACATION
                elif EVENT_TELEWORK.lower() in event_message.lower():
                    next_day_type = EVENT_TELEWORK
                else:
                    next_day_type = event_message

        # Auto-update mode (skip if manually set to absence mode)
        if self._day_mode == self._mode_absence:
            _LOGGER.debug(
                "Periodic check: auto-update skipped, absence mode active ('%s')",
                self._day_mode,
            )
        else:
            new_mode = await self._determine_mode(next_day_type)
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

        return self._build_result(next_day_type=next_day_type)

    def _build_result(self, next_day_type: str) -> dict:
        """Build the data dict returned by the coordinator."""
        return {
            "next_day_type": next_day_type,
            "current_event": self._current_event,
            "event_period": self._event_period,
            "day_mode": self._day_mode,
            "thermostat_mode": self._thermostat_mode,
        }

    async def _determine_mode(self, next_day_type: str) -> str | None:
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
        holiday_calendar = self.entry.data.get(CONF_HOLIDAY_CALENDAR)
        is_holiday = False
        if holiday_calendar:
            holiday_state = self.hass.states.get(holiday_calendar)
            if holiday_state and holiday_state.state == "on":
                is_holiday = True

        # 1. Check event_mode_map for the current event type
        if next_day_type and next_day_type != EVENT_NONE:
            mapped_mode = self._event_mode_map.get(next_day_type.lower())
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
        """Refresh schedulers based on current modes."""
        _LOGGER.info(
            "Refreshing schedulers: day_mode=%s, thermostat_mode=%s",
            self._day_mode,
            self._thermostat_mode,
        )

        # This is a placeholder for scheduler refresh logic
        # In a real implementation, this would:
        # 1. Find all scheduler switches with matching tags
        # 2. Turn off all schedulers
        # 3. Turn on schedulers matching current day_mode and thermostat_mode
        pass
