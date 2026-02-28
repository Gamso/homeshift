"""Sensor platform for Day Mode integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_NEXT_DAY_TYPE, EVENT_NONE
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

    _attr_has_entity_name = True
    _attr_translation_key = "next_day_type"

    def __init__(self, coordinator: DayModeCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_DAY_TYPE}"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get("next_day_type", EVENT_NONE)

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
            "day_mode": self.coordinator.day_mode,
            "thermostat_mode": self.coordinator.thermostat_mode,
            "current_event": self.coordinator.current_event,
            "event_period": self.coordinator.event_period,
        }
