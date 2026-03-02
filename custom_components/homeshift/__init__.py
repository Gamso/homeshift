"""The HomeShift integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant

from .const import DOMAIN, SERVICE_REFRESH_SCHEDULERS, SERVICE_SYNC_CALENDAR
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeShift from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator
    coordinator = HomeShiftCoordinator(hass, entry)
    await coordinator.async_restore_state()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass, coordinator)

    # Reload the integration when options are saved so the coordinator picks up changes
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_update))

    # Once HA is fully started (all entities available), run a calendar sync so that
    # day_mode reflects the current calendar state rather than just the restored value.
    if hass.state == CoreState.running:
        # Integration was loaded/reloaded while HA was already running; sync now.
        hass.async_create_task(coordinator.async_sync_calendar())
    else:
        # HA is still starting — schedule the sync for when all entities are ready.
        async def _async_ha_started(_event: Event) -> None:
            await coordinator.async_sync_calendar()

        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_ha_started)
        )

    _LOGGER.info("HomeShift integration loaded successfully (entry_id=%s)", entry.entry_id)

    return True


async def _async_reload_on_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup_services(hass: HomeAssistant, coordinator: HomeShiftCoordinator) -> None:
    """Set up services for the HomeShift integration."""

    async def handle_refresh_schedulers(_call) -> None:
        """Handle the refresh_schedulers service call."""
        _LOGGER.info("Service call: refresh_schedulers")
        await coordinator.async_refresh_schedulers()

    async def handle_sync_calendar(_call) -> None:
        """Handle the sync_calendar service call."""
        _LOGGER.info("Service call: sync_calendar")
        await coordinator.async_sync_calendar()

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_SCHEDULERS, handle_refresh_schedulers
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_CALENDAR, handle_sync_calendar
    )
