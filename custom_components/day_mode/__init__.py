"""The Day Mode integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_CHECK_TIME, DEFAULT_CHECK_TIME
from .coordinator import DayModeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Day Mode from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create coordinator
    coordinator = DayModeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Forward the setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up daily check for next day type
    check_time = entry.data.get(CONF_CHECK_TIME, DEFAULT_CHECK_TIME)
    _LOGGER.info(f"Setting up daily check at {check_time}")
    
    # Register services
    await async_setup_services(hass, coordinator)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_setup_services(hass: HomeAssistant, coordinator: DayModeCoordinator) -> None:
    """Set up services for the Day Mode integration."""
    from .const import SERVICE_REFRESH_SCHEDULERS, SERVICE_CHECK_NEXT_DAY
    
    async def handle_refresh_schedulers(call):
        """Handle the refresh_schedulers service call."""
        await coordinator.async_refresh_schedulers()
    
    async def handle_check_next_day(call):
        """Handle the check_next_day service call."""
        await coordinator.async_check_next_day()
    
    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_SCHEDULERS, handle_refresh_schedulers
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CHECK_NEXT_DAY, handle_check_next_day
    )
