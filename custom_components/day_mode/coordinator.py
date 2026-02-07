"""Coordinator for Day Mode integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_change, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODES,
    CONF_THERMOSTAT_MODES,
    DEFAULT_DAY_MODES,
    DEFAULT_THERMOSTAT_MODES,
    EVENT_VACANCES,
    EVENT_TELETRAVAIL,
)

_LOGGER = logging.getLogger(__name__)


class DayModeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Day Mode data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self._mode_jour: str = DEFAULT_DAY_MODES[0]  # Default to "Maison"
        self._mode_thermostat: str = DEFAULT_THERMOSTAT_MODES[0]  # Default to "Eteint"
        
        # Parse day modes and thermostat modes from config
        day_modes_str = entry.data.get(CONF_DAY_MODES, ", ".join(DEFAULT_DAY_MODES))
        self._day_modes = [mode.strip() for mode in day_modes_str.split(",")]
        
        thermostat_modes_str = entry.data.get(CONF_THERMOSTAT_MODES, ", ".join(DEFAULT_THERMOSTAT_MODES))
        self._thermostat_modes = [mode.strip() for mode in thermostat_modes_str.split(",")]
        
        # Set up daily check
        self._setup_daily_check()

    def _setup_daily_check(self) -> None:
        """Set up daily check for next day type."""
        # Schedule daily check at 00:10
        async_track_time_change(
            self.hass,
            self._handle_daily_check,
            hour=0,
            minute=10,
            second=0,
        )

    @callback
    async def _handle_daily_check(self, now) -> None:
        """Handle daily check."""
        await self.async_check_next_day()

    @property
    def day_modes(self) -> list[str]:
        """Return configured day modes."""
        return self._day_modes

    @property
    def thermostat_modes(self) -> list[str]:
        """Return configured thermostat modes."""
        return self._thermostat_modes

    @property
    def mode_jour(self) -> str:
        """Return current day mode."""
        return self._mode_jour

    @property
    def mode_thermostat(self) -> str:
        """Return current thermostat mode."""
        return self._mode_thermostat

    async def async_set_mode_jour(self, mode: str) -> None:
        """Set day mode."""
        if mode in self._day_modes:
            self._mode_jour = mode
            await self.async_refresh_schedulers()
            self.async_set_updated_data(self.data)

    async def async_set_mode_thermostat(self, mode: str) -> None:
        """Set thermostat mode."""
        if mode in self._thermostat_modes:
            self._mode_thermostat = mode
            await self.async_refresh_schedulers()
            self.async_set_updated_data(self.data)

    async def _async_update_data(self) -> dict:
        """Fetch data from calendar."""
        calendar_entity = self.entry.data.get(CONF_CALENDAR_ENTITY)
        
        if not calendar_entity:
            return {
                "next_day_type": "Aucun",
                "mode_jour": self._mode_jour,
                "mode_thermostat": self._mode_thermostat,
            }
        
        # Get calendar state
        calendar_state = self.hass.states.get(calendar_entity)
        if not calendar_state:
            return {
                "next_day_type": "Aucun",
                "mode_jour": self._mode_jour,
                "mode_thermostat": self._mode_thermostat,
            }
        
        # Check for events
        event_start = calendar_state.attributes.get("start_time")
        event_message = calendar_state.attributes.get("message")
        
        next_day_type = "Aucun"
        
        if event_start:
            try:
                # Parse event start time
                event_date = event_start.split(" ")[0]
                today = datetime.now().date().isoformat()
                
                if event_date == today:
                    if event_message == EVENT_VACANCES:
                        next_day_type = EVENT_VACANCES
                    elif event_message == EVENT_TELETRAVAIL:
                        next_day_type = EVENT_TELETRAVAIL
            except Exception as e:
                _LOGGER.error(
                    f"Error parsing calendar event from {calendar_entity}: {e}. "
                    f"Event data: start_time={event_start}, message={event_message}"
                )
        
        return {
            "next_day_type": next_day_type,
            "mode_jour": self._mode_jour,
            "mode_thermostat": self._mode_thermostat,
        }

    async def async_check_next_day(self) -> None:
        """Check and set next day type."""
        # Don't change if mode is "Absence"
        if self._mode_jour == "Absence":
            _LOGGER.info("Mode is Absence, skipping next day check")
            return
        
        await self.async_refresh()
        next_day_type = self.data.get("next_day_type", "Aucun")
        
        # Priority: Vacances > Weekend > Télétravail > Holiday > Travail
        now = datetime.now()
        is_weekend = now.weekday() in [5, 6]  # Saturday or Sunday
        
        # Check for holiday calendar
        holiday_calendar = self.entry.data.get(CONF_HOLIDAY_CALENDAR)
        is_holiday = False
        if holiday_calendar:
            holiday_state = self.hass.states.get(holiday_calendar)
            if holiday_state and holiday_state.state == "on":
                is_holiday = True
        
        new_mode = None
        
        if next_day_type == EVENT_VACANCES:
            new_mode = "Maison"
        elif is_weekend:
            new_mode = "Maison"
        elif next_day_type == EVENT_TELETRAVAIL:
            new_mode = "Télétravail"
        elif is_holiday:
            new_mode = "Maison"
        else:
            new_mode = "Travail"
        
        if new_mode and new_mode in self._day_modes:
            _LOGGER.info(f"Setting mode_jour to {new_mode}")
            await self.async_set_mode_jour(new_mode)

    async def async_refresh_schedulers(self) -> None:
        """Refresh schedulers based on current modes."""
        _LOGGER.info(
            f"Refreshing schedulers: mode_jour={self._mode_jour}, "
            f"mode_thermostat={self._mode_thermostat}"
        )
        
        # This is a placeholder for scheduler refresh logic
        # In a real implementation, this would:
        # 1. Find all scheduler switches with matching tags
        # 2. Turn off all schedulers
        # 3. Turn on schedulers matching current mode_jour and mode_thermostat
        
        # The actual implementation would require:
        # - Finding switches with specific naming patterns or tags
        # - Calling switch.turn_on/turn_off services
        # - Potentially controlling climate entities based on thermostat mode
        
        # Example logic (commented out as it depends on user's setup):
        # mode_jour_normalized = self._mode_jour.lower().replace('é', 'e')
        # scheduler_pattern = f"switch.schedulers_{self._mode_thermostat.lower()}_{mode_jour_normalized}"
        # # Find and control matching switches
        
        pass
