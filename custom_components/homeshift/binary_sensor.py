"""Binary sensor platform for HomeShift integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import BINARY_SENSOR_COVER_HEAT_ACTIVE, CONF_COVER_ENTITIES, CONF_COVER_TEMP_SENSOR, DOMAIN
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeShift binary sensor entities."""
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **entry.options}
    entities = []
    if config.get(CONF_COVER_ENTITIES) and config.get(CONF_COVER_TEMP_SENSOR):
        entities.append(HomeShiftCoverHeatActiveSensor(coordinator, entry))
    async_add_entities(entities)


def _device_info(entry: ConfigEntry) -> dict:
    """Return shared device info dict."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "HomeShift",
        "manufacturer": "Gamso",
        "model": "HomeShift",
    }


class HomeShiftCoverHeatActiveSensor(CoordinatorEntity[HomeShiftCoordinator], BinarySensorEntity):
    """Binary sensor: True when cover heat protection conditions are currently met.

    Active (on) when the current time is within the daily cover open/close
    window (from Daily Cover Schedule) AND the outdoor temperature exceeds
    the configured threshold.
    Updates every coordinator poll cycle and also immediately whenever the
    temperature sensor value changes.
    """

    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_has_entity_name = True
    _attr_name = "Cover Heat Active"
    _attr_icon = "mdi:sun-thermometer"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_COVER_HEAT_ACTIVE}"
        self._entry = entry

    async def async_added_to_hass(self) -> None:
        """Register extra listener on the temperature sensor for real-time updates."""
        await super().async_added_to_hass()
        config = {**self._entry.data, **self._entry.options}
        temp_sensor = config.get(CONF_COVER_TEMP_SENSOR, "")
        if temp_sensor:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [temp_sensor],
                    self._on_temp_change,
                )
            )

    @callback
    def _on_temp_change(self, _event) -> None:
        """Re-evaluate and push state when the temperature sensor changes."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return True when heat protection conditions are met."""
        return self.coordinator.is_heat_protection_active(dt_util.now())

    @property
    def device_info(self) -> dict:
        """Return device information."""
        return _device_info(self._entry)
