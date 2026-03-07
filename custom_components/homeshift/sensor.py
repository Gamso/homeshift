"""Sensor platform for HomeShift integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_NEXT_SCAN, SENSOR_NEXT_MODE, SENSOR_NEXT_MODE_AT
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeShift sensor entities."""
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HomeShiftNextScanSensor(coordinator, entry),
            HomeShiftNextModeSensor(coordinator, entry),
            HomeShiftNextModeAtSensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> dict:
    """Return shared device info dict."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "HomeShift",
        "manufacturer": "Gamso",
        "model": "HomeShift",
    }


class HomeShiftNextScanSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """Timestamp sensor: when the next calendar scan is scheduled."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_name = "Next Scan"
    _attr_icon = "mdi:calendar-sync"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_SCAN}"
        self._entry = entry

    @property
    def native_value(self) -> datetime | None:
        """Return the next scheduled scan timestamp."""
        return self.coordinator.next_scan_at

    @property
    def device_info(self) -> dict:
        """Return device information."""
        return _device_info(self._entry)


class HomeShiftNextModeSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """String sensor: the day mode predicted at the next automatic change."""

    _attr_has_entity_name = True
    _attr_name = "Next Mode"
    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_MODE}"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return the predicted mode at the next change."""
        return self.coordinator.next_mode_predicted

    @property
    def device_info(self) -> dict:
        """Return device information."""
        return _device_info(self._entry)


class HomeShiftNextModeAtSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """Timestamp sensor: when the next day mode change is expected."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_name = "Next Mode At"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_MODE_AT}"
        self._entry = entry

    @property
    def native_value(self) -> datetime | None:
        """Return when the next mode change is expected."""
        return self.coordinator.next_mode_at

    @property
    def device_info(self) -> dict:
        """Return device information."""
        return _device_info(self._entry)
