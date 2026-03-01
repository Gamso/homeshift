"""Select platform for HomeShift integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SELECT_DAY_MODE, SELECT_THERMOSTAT_MODE
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeShift select entities."""
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            HomeShiftSelect(coordinator, entry),
            HomeShiftThermostatSelect(coordinator, entry),
        ]
    )


class HomeShiftSelect(CoordinatorEntity[HomeShiftCoordinator], SelectEntity):
    """Representation of Day Mode select entity."""

    _attr_has_entity_name = True
    _attr_name = "Day Mode"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SELECT_DAY_MODE}"
        self._attr_options = coordinator.day_modes
        self._entry = entry

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.day_mode

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the key→display map so custom cards can translate mode keys."""
        return {"day_mode_map": self.coordinator.day_mode_map}

    def select_option(self, option: str) -> None:
        """Change the selected option (sync stub — async_select_option is used)."""
        raise NotImplementedError

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_set_day_mode(option)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HomeShift",
            "manufacturer": "Gamso",
            "model": "HomeShift Controller",
        }


class HomeShiftThermostatSelect(CoordinatorEntity[HomeShiftCoordinator], SelectEntity):
    """Representation of Thermostat Mode select entity."""

    _attr_has_entity_name = True
    _attr_name = "Thermostat Mode"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SELECT_THERMOSTAT_MODE}"
        self._attr_options = coordinator.thermostat_modes
        self._entry = entry

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.thermostat_mode

    def select_option(self, option: str) -> None:
        """Change the selected option (sync stub — async_select_option is used)."""
        raise NotImplementedError

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_set_thermostat_mode(option)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HomeShift",
            "manufacturer": "Gamso",
            "model": "HomeShift Controller",
        }
