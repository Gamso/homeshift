"""The HomeShift integration."""
from __future__ import annotations

import logging
from datetime import datetime

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DURATION,
    ATTR_UNTIL,
    CLOSE_ELEVATION_MAX,
    CLOSE_ELEVATION_MIN,
    CONF_DAILY_COVER_CLOSE_ELEVATION,
    CONF_DAILY_COVER_CLOSE_MODE,
    CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES,
    CONF_DAILY_COVER_ENTITIES,
    CONF_DAILY_COVER_ITEMS,
    CONF_DAY_MODE_MAP,
    CONF_ITEM_COVER,
    CONF_ITEM_MY_BUTTON,
    CONF_ITEM_WINDOW_SENSOR,
    CONF_SCHEDULERS_PER_MODE,
    DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
    DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES,
    DOMAIN,
    LEGACY_CLOSE_MODE_ELEVATION,
    LOCALIZED_DEFAULTS,
    SENSOR_NEXT_SCAN,
    SERVICE_CLOSE_COVERS,
    SERVICE_INHIBIT_COVERS,
    SERVICE_OPEN_COVERS,
    SERVICE_REFRESH_SCHEDULERS,
    SERVICE_RESUME_COVERS,
    SERVICE_SYNC_CALENDAR,
    get_localized_defaults,
    parse_key_value_map,
)
from . import coordinator as coordinator_module, cover_manager as cover_manager_module
from .coordinator import HomeShiftCoordinator
from .cover_manager import elevation_for_sunset_offset

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

SERVICES = (
    SERVICE_REFRESH_SCHEDULERS,
    SERVICE_SYNC_CALENDAR,
    SERVICE_OPEN_COVERS,
    SERVICE_CLOSE_COVERS,
    SERVICE_INHIBIT_COVERS,
    SERVICE_RESUME_COVERS,
)

# With neither a duration nor an end date, an inhibition lasts until resumed.
INHIBIT_COVERS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Exclusive(ATTR_DURATION, "end"): cv.positive_time_period,
        vol.Exclusive(ATTR_UNTIL, "end"): cv.datetime,
    }
)
# Without entity_id, every inhibited cover is resumed.
RESUME_COVERS_SCHEMA = vol.Schema({vol.Optional("entity_id"): cv.entity_ids})

# Settings the v3 -> v4 migration folds into CONF_DAILY_COVER_CLOSE_ELEVATION.
_RETIRED_CLOSE_KEYS = frozenset({CONF_DAILY_COVER_CLOSE_MODE, CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES})


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

    if entry.version < 4:
        # v3 -> v4: the evening close no longer takes a delay in minutes
        # around sunset, only the sun elevation to close at. Convert the
        # stored offset into the elevation it was landing on, so the covers
        # keep moving at the time they moved yesterday.
        merged = {**entry.data, **entry.options}
        elevation = _migrated_close_elevation(hass, merged)

        data = {k: v for k, v in entry.data.items() if k not in _RETIRED_CLOSE_KEYS}
        options = {k: v for k, v in entry.options.items() if k not in _RETIRED_CLOSE_KEYS}
        if elevation is not None:
            options[CONF_DAILY_COVER_CLOSE_ELEVATION] = elevation

        hass.config_entries.async_update_entry(entry, data=data, options=options, version=4)
        _LOGGER.info(
            "HomeShift config entry migrated to version 4 (covers now close at %s° of sun elevation)",
            elevation,
        )

    if entry.version < 5:
        # v4 -> v5: schedulers were stored per day mode display label
        # ("Maison", "Work", ...). The label depends on the instance language
        # and on renames, and a form built without the localized defaults
        # stored the English labels while the coordinator ran on the French
        # ones — no scheduler ever matched. They are now stored per mode key.
        merged = {**entry.data, **entry.options}
        day_mode_map = parse_key_value_map(
            merged.get(CONF_DAY_MODE_MAP) or get_localized_defaults(hass)[CONF_DAY_MODE_MAP]
        )
        data = dict(entry.data)
        options = dict(entry.options)
        for store in (data, options):
            if store.get(CONF_SCHEDULERS_PER_MODE):
                store[CONF_SCHEDULERS_PER_MODE] = schedulers_by_mode_key(
                    store[CONF_SCHEDULERS_PER_MODE], day_mode_map
                )

        hass.config_entries.async_update_entry(entry, data=data, options=options, version=5)
        _LOGGER.info("HomeShift config entry migrated to version 5 (schedulers keyed by day mode key)")

    return True


def _mode_key_for_label(label: str, day_mode_map: dict[str, str]) -> str | None:
    """Return the day mode key a stored scheduler label stands for, or None.

    Tried in order: the label already is a key, it is the current display
    name of a key, it is a key spelled with another case, or it is one of the
    default display names of any supported language (what the form stored
    when it was built without the localized defaults).
    """
    if label in day_mode_map:
        return label
    for key, display in day_mode_map.items():
        if display == label:
            return key
    lowered = label.lower()
    for key in day_mode_map:
        if key.lower() == lowered:
            return key
    for defaults in LOCALIZED_DEFAULTS.values():
        for key, display in parse_key_value_map(defaults[CONF_DAY_MODE_MAP]).items():
            if display == label and key in day_mode_map:
                return key
    return None


def schedulers_by_mode_key(schedulers: dict, day_mode_map: dict[str, str]) -> dict[str, list]:
    """Re-key a {label: [switch, ...]} scheduler map by day mode key.

    Two labels resolving to the same key have their switches merged, in
    order and without duplicates. A label that matches no mode is kept as is
    (and logged): dropping it would silently lose the user's assignment.
    """
    result: dict[str, list] = {}
    for label, switches in schedulers.items():
        key = _mode_key_for_label(str(label), day_mode_map)
        if key is None:
            _LOGGER.warning(
                "HomeShift migration: schedulers stored under '%s' match no day mode (%s) — kept as is",
                label,
                day_mode_map,
            )
            key = str(label)
        merged = result.setdefault(key, [])
        for switch in switches or []:
            if switch not in merged:
                merged.append(switch)
    return result


def _migrated_close_elevation(hass: HomeAssistant, merged: dict) -> float | None:
    """Return the elevation a v3 entry should close at, or None to leave it unset.

    An entry that already picked an elevation keeps it. Otherwise the stored
    sunset offset — or the default the entry was silently running on — is
    converted to the elevation it lands on, clamped to what the config flow
    accepts. Returns None when the daily schedule drives no cover, so an
    unused feature is not given a setting it never had.
    """
    if not merged.get(CONF_DAILY_COVER_ITEMS):
        return None

    if merged.get(CONF_DAILY_COVER_CLOSE_MODE) == LEGACY_CLOSE_MODE_ELEVATION:
        try:
            return float(merged[CONF_DAILY_COVER_CLOSE_ELEVATION])
        except (KeyError, TypeError, ValueError):
            pass

    try:
        offset = int(merged.get(CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES, DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES))
    except (TypeError, ValueError):
        offset = DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES

    elevation = elevation_for_sunset_offset(hass, offset, dt_util.now().year)
    if elevation is None:
        _LOGGER.warning(
            "HomeShift: could not convert the %s min sunset offset to a sun elevation "
            "(no usable location) — falling back to %s°",
            offset,
            DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
        )
        return DEFAULT_DAILY_COVER_CLOSE_ELEVATION

    clamped = min(max(elevation, CLOSE_ELEVATION_MIN), CLOSE_ELEVATION_MAX)
    if clamped != elevation:
        _LOGGER.warning(
            "HomeShift: a %s min sunset offset works out to %s° of sun elevation, outside the "
            "%s°..%s° the config flow accepts — clamped to %s°",
            offset,
            elevation,
            CLOSE_ELEVATION_MIN,
            CLOSE_ELEVATION_MAX,
            clamped,
        )
    return clamped


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeShift from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator
    coordinator = HomeShiftCoordinator(hass, entry)

    # The first refresh arms the next-mode and cover timers. Register their
    # cancellation first: if that refresh fails (ConfigEntryNotReady), HA
    # runs the unload callbacks registered so far and retries with a new
    # coordinator; registered afterwards, the orphan's timers would still
    # fire and drive real switches and covers.
    entry.async_on_unload(coordinator.async_cancel_next_mode_timer)
    entry.async_on_unload(coordinator.async_cancel_cover_timers)

    await coordinator.async_restore_state()
    await coordinator.cover_manager.async_restore_state()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async_setup_services(hass)

    # React immediately when the temperature sensor changes (no need to wait for the poll)
    entry.async_on_unload(coordinator.cover_manager.async_setup_listeners())

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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the entry's persisted state when the integration is removed.

    The coordinator and the cover manager each keep a store named after the
    entry id; nothing else would ever delete them.
    """
    for module in (coordinator_module, cover_manager_module):
        await Store(hass, module.STORAGE_VERSION, f"{module.STORAGE_KEY}.{entry.entry_id}").async_remove()


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
            for service in SERVICES:
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

    async def handle_open_covers(_call) -> None:
        """Open the daily-schedule covers now, whatever the time or the mode."""
        _LOGGER.info("Service call: open_covers")
        for coordinator in _coordinators():
            await coordinator.async_open_covers()

    async def handle_close_covers(_call) -> None:
        """Close the daily-schedule covers now, like the evening close."""
        _LOGGER.info("Service call: close_covers")
        for coordinator in _coordinators():
            await coordinator.async_close_covers()

    hass.services.async_register(DOMAIN, SERVICE_OPEN_COVERS, handle_open_covers)
    hass.services.async_register(DOMAIN, SERVICE_CLOSE_COVERS, handle_close_covers)

    async def handle_inhibit_covers(call: ServiceCall) -> None:
        """Take the given covers out of the automation for a while."""
        covers: list[str] = call.data["entity_id"]
        until = _inhibition_end(call.data)
        targets = _coordinators_for(covers)
        _LOGGER.info("Service call: inhibit_covers %s until %s", covers, until or "resumed")
        for coordinator, managed in targets:
            await coordinator.async_inhibit_covers(managed, until)

    async def handle_resume_covers(call: ServiceCall) -> None:
        """Hand the given covers (or all of them) back to the automation."""
        covers: list[str] | None = call.data.get("entity_id")
        _LOGGER.info("Service call: resume_covers %s", covers or "(all)")
        for coordinator in _coordinators():
            await coordinator.async_resume_covers(covers)

    def _coordinators_for(covers: list[str]) -> list[tuple[HomeShiftCoordinator, list[str]]]:
        """Pair each coordinator with the given covers it manages; refuse unknown ones."""
        targets: list[tuple[HomeShiftCoordinator, list[str]]] = []
        claimed: set[str] = set()
        for coordinator in _coordinators():
            managed = [cover for cover in covers if cover in coordinator.managed_covers]
            if managed:
                targets.append((coordinator, managed))
                claimed.update(managed)
        unknown = [cover for cover in covers if cover not in claimed]
        if unknown:
            raise ServiceValidationError(
                f"HomeShift does not drive {', '.join(unknown)} — only the covers of the daily "
                "schedule and of heat protection can be inhibited",
                translation_domain=DOMAIN,
                translation_key="cover_not_managed",
                translation_placeholders={"covers": ", ".join(unknown)},
            )
        return targets

    hass.services.async_register(
        DOMAIN, SERVICE_INHIBIT_COVERS, handle_inhibit_covers, schema=INHIBIT_COVERS_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESUME_COVERS, handle_resume_covers, schema=RESUME_COVERS_SCHEMA
    )


def _inhibition_end(data: dict) -> datetime | None:
    """Return when an inhibit_covers call ends, or None for "until resumed".

    A date given without a time zone is read in Home Assistant's own zone,
    which is what the UI date picker means. An end already past is refused:
    it would inhibit nothing while looking like it worked.
    """
    now = dt_util.now()
    if ATTR_DURATION in data:
        until = now + data[ATTR_DURATION]
    elif ATTR_UNTIL in data:
        until = data[ATTR_UNTIL]
        if until.tzinfo is None:
            until = until.replace(tzinfo=dt_util.get_default_time_zone())
    else:
        return None
    if until <= now:
        raise ServiceValidationError(
            "The end of the inhibition must be in the future",
            translation_domain=DOMAIN,
            translation_key="inhibition_end_in_past",
        )
    return until
