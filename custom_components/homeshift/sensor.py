"""Sensor platform for HomeShift integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_NEXT_DAY_TYPE
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeShift sensor entities."""
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([HomeShiftNextDayTypeSensor(coordinator, entry)])


class HomeShiftNextDayTypeSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """Sensor for next day type detection."""

    _attr_has_entity_name = True
    _attr_name = "Next Day Type"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_DAY_TYPE}"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get("next_day_type", self.coordinator._event_none)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HomeShift",
            "manufacturer": "Gamso",
            "model": "HomeShift Controller",
        }

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "day_mode": self.coordinator.day_mode,
            "thermostat_mode": self.coordinator.thermostat_mode,
            "thermostat_mode_key": self.coordinator.thermostat_mode_key,
            "current_event": self.coordinator.current_event,
            "event_period": self.coordinator.event_period,
            "override_until": self.coordinator.data.get("override_until") if self.coordinator.data else None,
        }
