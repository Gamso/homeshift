"""The HomeShift integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DAILY_COVER_ENTITIES,
    CONF_DAILY_COVER_ITEMS,
    CONF_ITEM_COVER,
    CONF_ITEM_MY_BUTTON,
    CONF_ITEM_WINDOW_SENSOR,
    DOMAIN,
    SENSOR_NEXT_SCAN,
    SERVICE_REFRESH_SCHEDULERS,
    SERVICE_SYNC_CALENDAR,
)
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.NUMBER, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to the current version."""
    _LOGGER.debug("Migrating HomeShift config entry from version %s", entry.version)

    if entry.version < 2:
        # v1 → v2: remove the deprecated "Next Scan" sensor entity
        ent_reg = er.async_get(hass)
        unique_id = f"{entry.entry_id}_{SENSOR_NEXT_SCAN}"
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id:
            ent_reg.async_remove(entity_id)
            _LOGGER.info("Removed deprecated 'Next Scan' sensor entity (%s)", entity_id)

        hass.config_entries.async_update_entry(entry, version=2)
        _LOGGER.info("HomeShift config entry migrated to version 2")

    if entry.version < 3:
        # v2 → v3: the flat "Daily Cover Entities" list and the per-cover list
        # were two ways of saying the same thing. Fold the former into the
        # latter, where each cover can also carry a window sensor and a My
        # position button.
        merged = {**entry.data, **entry.options}
        items = [
            dict(item)
            for item in (merged.get(CONF_DAILY_COVER_ITEMS) or [])
            if isinstance(item, dict) and item.get(CONF_ITEM_COVER)
        ]
        known = {item[CONF_ITEM_COVER] for item in items}
        for entity_id in merged.get(CONF_DAILY_COVER_ENTITIES) or []:
            if entity_id and entity_id not in known:
                items.append(
                    {
                        CONF_ITEM_COVER: entity_id,
                        CONF_ITEM_WINDOW_SENSOR: "",
                        CONF_ITEM_MY_BUTTON: "",
                    }
                )
                known.add(entity_id)

        data = {k: v for k, v in entry.data.items() if k != CONF_DAILY_COVER_ENTITIES}
        options = {k: v for k, v in entry.options.items() if k != CONF_DAILY_COVER_ENTITIES}
        if items:
            # Options win over data in the merged view, so that is where the
            # single list belongs.
            options[CONF_DAILY_COVER_ITEMS] = items

        hass.config_entries.async_update_entry(entry, data=data, options=options, version=3)
        _LOGGER.info(
            "HomeShift config entry migrated to version 3 (%d cover(s) in the daily schedule)",
            len(items),
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeShift from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator
    coordinator = HomeShiftCoordinator(hass, entry)
    await coordinator.async_restore_state()
    await coordinator._cover_manager.async_restore_state()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async_setup_services(hass)

    # Cancel the next-mode timer when the entry is unloaded
    entry.async_on_unload(coordinator.async_cancel_next_mode_timer)

    # Cancel the cover open/close timers when the entry is unloaded
    entry.async_on_unload(coordinator.async_cancel_cover_timers)

    # React immediately when the temperature sensor changes (no need to wait for the poll)
    entry.async_on_unload(coordinator._cover_manager.async_setup_listeners())

    # Reload the integration when options are saved so the coordinator picks up changes
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_update))

    # Once HA is fully started (all entities available), run a calendar sync so that
    # day_mode reflects the current calendar state rather than just the restored value.
    if hass.state == CoreState.running:
        # Integration was loaded/reloaded while HA was already running; sync now.
        hass.async_create_task(coordinator.async_sync_calendar())
    else:
        # HA is still starting — schedule the sync for when all entities are ready.
        # Use a mutable container so the callback can clear the cancel reference
        # synchronously when the event fires.  This prevents the async_on_unload
        # guard from calling an already-removed one-shot listener and logging
        # "Unable to remove unknown job listener" on the next reload.
        _ha_started_cancel: list = [None]

        @callback
        def _ha_started_cb(_event: Event) -> None:
            _ha_started_cancel[0] = None  # fired — disable the cancel guard
            hass.async_create_task(coordinator.async_sync_calendar())

        _ha_started_cancel[0] = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _ha_started_cb
        )

        @callback
        def _cancel_ha_started() -> None:
            """Cancel the start listener — safe to call after the event has fired."""
            if _ha_started_cancel[0] is not None:
                _ha_started_cancel[0]()
                _ha_started_cancel[0] = None

        entry.async_on_unload(_cancel_ha_started)

    _LOGGER.info("HomeShift integration loaded successfully (entry_id=%s)", entry.entry_id)

    return True


async def _async_reload_on_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            # Last entry gone: drop the services too. Left registered, they
            # would still appear in the UI and act on an unloaded coordinator
            # (writing to its store, calling cover/switch services).
            hass.data.pop(DOMAIN)
            for service in (SERVICE_REFRESH_SCHEDULERS, SERVICE_SYNC_CALENDAR):
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the HomeShift services.

    The handlers resolve the loaded coordinators at call time rather than
    capturing one: a captured coordinator outlives its entry (a reload builds
    a new one) and would keep answering service calls after being unloaded.
    """

    def _coordinators() -> list[HomeShiftCoordinator]:
        return list(hass.data.get(DOMAIN, {}).values())

    async def handle_refresh_schedulers(_call) -> None:
        """Handle the refresh_schedulers service call."""
        _LOGGER.info("Service call: refresh_schedulers")
        for coordinator in _coordinators():
            await coordinator.async_refresh_schedulers()

    async def handle_sync_calendar(_call) -> None:
        """Handle the sync_calendar service call."""
        _LOGGER.info("Service call: sync_calendar")
        for coordinator in _coordinators():
            await coordinator.async_sync_calendar()

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_SCHEDULERS, handle_refresh_schedulers
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_CALENDAR, handle_sync_calendar
    )
