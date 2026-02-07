"""Sensor platform for Day Mode integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_NEXT_DAY_TYPE
from .coordinator import DayModeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Day Mode sensor entities."""
    coordinator: DayModeCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([NextDayTypeSensor(coordinator, entry)])


class NextDayTypeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next day type detection."""

    def __init__(self, coordinator: DayModeCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Next Day Type"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_DAY_TYPE}"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get("next_day_type", "Aucun")

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Day Mode",
            "manufacturer": "Gamso",
            "model": "Day Mode Controller",
        }

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "mode_jour": self.coordinator.mode_jour,
            "mode_thermostat": self.coordinator.mode_thermostat,
        }
