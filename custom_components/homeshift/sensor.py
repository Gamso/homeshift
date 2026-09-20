"""Sensor platform for HomeShift integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CLOSE_TRIGGER_ELEVATION,
    CONF_DAILY_COVER_CLOSE_ELEVATION,
    CONF_DAILY_COVER_ITEMS,
    DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
    DOMAIN,
    SENSOR_COVER_CLOSE_TIME,
    SENSOR_COVER_OPEN_TIME,
    SENSOR_NEXT_MODE,
    SENSOR_NEXT_MODE_AT,
)
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeShift sensor entities."""
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HomeShiftNextModeSensor(coordinator, entry),
        HomeShiftNextModeAtSensor(coordinator, entry),
    ]
    config = {**entry.data, **entry.options}
    if _daily_covers_configured(config):
        entities.append(HomeShiftCoverOpenTimeSensor(coordinator, entry))
        entities.append(HomeShiftCoverCloseTimeSensor(coordinator, entry))
    async_add_entities(entities)


def _daily_covers_configured(config: dict) -> bool:
    """Return True when at least one cover is configured for the daily schedule."""
    return bool(config.get(CONF_DAILY_COVER_ITEMS))


def _device_info(entry: ConfigEntry) -> dict:
    """Return shared device info dict."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "HomeShift",
        "manufacturer": "Gamso",
        "model": "HomeShift",
    }


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


class HomeShiftCoverOpenTimeSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """String sensor: the scheduled cover opening time for today.

    Only registered when the daily schedule drives at least one cover
    (CONF_DAILY_COVER_ITEMS).
    Updated each morning when async_compute_daily_schedule() runs.
    """

    _attr_has_entity_name = True
    _attr_name = "Cover Open Time"
    _attr_icon = "mdi:roller-shade"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_COVER_OPEN_TIME}"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return today's computed cover opening time (HH:MM)."""
        return self.coordinator.cover_open_time

    @property
    def device_info(self) -> dict:
        """Return device information."""
        return _device_info(self._entry)


class HomeShiftCoverCloseTimeSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """String sensor: the estimated daily cover closing time for today.

    Only registered when the daily schedule drives at least one cover
    (CONF_DAILY_COVER_ITEMS).
    Updated each morning when async_compute_daily_schedule() runs: the time
    the setting sun reaches CONF_DAILY_COVER_CLOSE_ELEVATION. The attributes
    report the configured elevation, and whether it is what produced tonight's
    time — a day the sun never reaches it closes at plain sunset instead, and
    that has to be visible rather than silent.
    """

    _attr_has_entity_name = True
    _attr_name = "Cover Close Time"
    _attr_icon = "mdi:roller-shade-closed"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_COVER_CLOSE_TIME}"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return today's estimated cover closing time (HH:MM)."""
        return self.coordinator.cover_close_time

    @property
    def extra_state_attributes(self) -> dict:
        """Return the configured elevation and what produced tonight's time."""
        config = {**self._entry.data, **self._entry.options}
        return {
            "sun_elevation": config.get(
                CONF_DAILY_COVER_CLOSE_ELEVATION, DEFAULT_DAILY_COVER_CLOSE_ELEVATION
            ),
            "trigger": self.coordinator.cover_close_trigger or CLOSE_TRIGGER_ELEVATION,
        }

    @property
    def device_info(self) -> dict:
        """Return device information."""
        return _device_info(self._entry)
