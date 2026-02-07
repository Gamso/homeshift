"""Select platform for Day Mode integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SELECT_MODE_JOUR, SELECT_MODE_THERMOSTAT
from .coordinator import DayModeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Day Mode select entities."""
    coordinator: DayModeCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            DayModeSelect(coordinator, entry),
            ThermostatModeSelect(coordinator, entry),
        ]
    )


class DayModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of Day Mode select entity."""

    def __init__(self, coordinator: DayModeCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_name = "Mode Jour"
        self._attr_unique_id = f"{entry.entry_id}_{SELECT_MODE_JOUR}"
        self._attr_options = coordinator.day_modes
        self._entry = entry

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.mode_jour

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_set_mode_jour(option)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Day Mode",
            "manufacturer": "Gamso",
            "model": "Day Mode Controller",
        }


class ThermostatModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of Thermostat Mode select entity."""

    def __init__(self, coordinator: DayModeCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_name = "Mode Thermostat"
        self._attr_unique_id = f"{entry.entry_id}_{SELECT_MODE_THERMOSTAT}"
        self._attr_options = coordinator.thermostat_modes
        self._entry = entry

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.mode_thermostat

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_set_mode_thermostat(option)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Day Mode",
            "manufacturer": "Gamso",
            "model": "Day Mode Controller",
        }
