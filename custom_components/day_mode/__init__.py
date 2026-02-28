"""The Day Mode integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
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

    # Register services
    await async_setup_services(hass, coordinator)

    _LOGGER.info("Day Mode integration loaded successfully (entry_id=%s)", entry.entry_id)

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
        _LOGGER.info("Service call: refresh_schedulers")
        await coordinator.async_refresh_schedulers()

    async def handle_check_next_day(call):
        """Handle the check_next_day service call."""
        _LOGGER.info("Service call: check_next_day")
        await coordinator.async_check_next_day()

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_SCHEDULERS, handle_refresh_schedulers
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CHECK_NEXT_DAY, handle_check_next_day
    )
