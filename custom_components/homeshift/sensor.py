"""Sensor platform for HomeShift integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CLOSE_TRIGGER_ELEVATION,
    CONF_DAILY_COVER_CLOSE_ELEVATION,
    CONF_DAILY_COVER_ITEMS,
    DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
    DOMAIN,
    SENSOR_COVER_CLOSE_TIME,
    SENSOR_COVER_OPEN_TIME,
    SENSOR_COVERS_INHIBITED,
    SENSOR_NEXT_MODE,
    SENSOR_NEXT_MODE_AT,
)
from .coordinator import HomeShiftCoordinator
from .entity import async_remove_stale_entities, setup_entity

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
    else:
        async_remove_stale_entities(hass, entry, SENSOR_DOMAIN, [SENSOR_COVER_OPEN_TIME, SENSOR_COVER_CLOSE_TIME])
    if coordinator.managed_covers:
        entities.append(HomeShiftCoversInhibitedSensor(coordinator, entry))
    else:
        async_remove_stale_entities(hass, entry, SENSOR_DOMAIN, [SENSOR_COVERS_INHIBITED])
    async_add_entities(entities)


def _daily_covers_configured(config: dict) -> bool:
    """Return True when at least one cover is configured for the daily schedule."""
    return bool(config.get(CONF_DAILY_COVER_ITEMS))


class HomeShiftNextModeSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """String sensor: the day mode predicted at the next automatic change."""

    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        setup_entity(self, entry, SENSOR_DOMAIN, SENSOR_NEXT_MODE)
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return the predicted mode at the next change."""
        return self.coordinator.next_mode_predicted


class HomeShiftNextModeAtSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """Timestamp sensor: when the next day mode change is expected."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        setup_entity(self, entry, SENSOR_DOMAIN, SENSOR_NEXT_MODE_AT)
        self._entry = entry

    @property
    def native_value(self) -> datetime | None:
        """Return when the next mode change is expected."""
        return self.coordinator.next_mode_at


class HomeShiftCoverOpenTimeSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """String sensor: the scheduled cover opening time for today.

    Only registered when the daily schedule drives at least one cover
    (CONF_DAILY_COVER_ITEMS).
    Updated each morning when async_compute_daily_schedule() runs.
    """

    _attr_icon = "mdi:roller-shade"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        setup_entity(self, entry, SENSOR_DOMAIN, SENSOR_COVER_OPEN_TIME)
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        """Return today's computed cover opening time (HH:MM)."""
        return self.coordinator.cover_open_time


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

    _attr_icon = "mdi:roller-shade-closed"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        setup_entity(self, entry, SENSOR_DOMAIN, SENSOR_COVER_CLOSE_TIME)
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


class HomeShiftCoversInhibitedSensor(CoordinatorEntity[HomeShiftCoordinator], SensorEntity):
    """Count of the covers taken out of the automation by hand.

    Only registered when HomeShift drives at least one cover (daily schedule
    or heat protection). The attributes carry what a dashboard needs to show
    and edit the inhibitions: each inhibited cover with its end (None until
    resumed), and every cover that can be inhibited. An inhibition that runs
    out disappears at the next poll.
    """

    _attr_icon = "mdi:window-shutter-cog"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        setup_entity(self, entry, SENSOR_DOMAIN, SENSOR_COVERS_INHIBITED)
        self._entry = entry

    @property
    def native_value(self) -> int:
        """Return how many covers are currently inhibited."""
        return len(self.coordinator.covers_inhibited(dt_util.now()))

    @property
    def extra_state_attributes(self) -> dict:
        """List the inhibited covers with their end, and the covers that can be inhibited."""
        inhibited = self.coordinator.covers_inhibited(dt_util.now())
        return {
            "covers": {cover: until.isoformat() if until else None for cover, until in inhibited.items()},
            "managed_covers": self.coordinator.managed_covers,
        }
