"""Helpers shared by the HomeShift entities."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

# Every entity id starts with this prefix, followed by the entity's
# translation key: select.homeshift_day_mode, sensor.homeshift_next_mode...
OBJECT_ID_PREFIX = "homeshift"


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the device grouping every HomeShift entity of an entry.

    HomeShift drives other entities and has no hardware of its own, hence a
    service device.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="HomeShift",
        manufacturer="Gamso",
        model="HomeShift",
        entry_type=DeviceEntryType.SERVICE,
    )


def setup_entity(entity: Entity, entry: ConfigEntry, platform: str, key: str) -> None:
    """Give an entity its unique id, translated name, device and entity id.

    The name comes from the `entity` section of the translations
    (translation_key), so it follows the instance language. Home Assistant
    would then derive the entity id from the name in that language for the
    languages it supports natively (French included), giving a French
    install select.homeshift_mode_jour. The entity id is therefore pinned
    to the English object id, the one the dashboards, the card and the
    README rely on. It only applies when the entity is first registered: an
    existing or renamed entity id is kept by the registry.
    """
    entity._attr_has_entity_name = True
    entity._attr_translation_key = key
    entity._attr_unique_id = f"{entry.entry_id}_{key}"
    entity._attr_device_info = device_info(entry)
    entity.entity_id = f"{platform}.{OBJECT_ID_PREFIX}_{key}"


@callback
def async_remove_stale_entities(hass: HomeAssistant, entry: ConfigEntry, platform: str, keys: list[str]) -> None:
    """Drop the registry entries of conditional entities no longer created.

    Some entities only exist while a feature is configured (the cover
    sensors, the heat protection sensor). Once the feature is removed from
    the options they are no longer added, but their registry entries stayed
    behind as "restored", unavailable entities.
    """
    registry = er.async_get(hass)
    for key in keys:
        entity_id = registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
        if entity_id is not None:
            registry.async_remove(entity_id)
