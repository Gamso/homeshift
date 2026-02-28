"""Number platform for HomeShift integration — override duration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, NUMBER_OVERRIDE_DURATION, DEFAULT_OVERRIDE_DURATION
from .coordinator import HomeShiftCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Day Mode number entities."""
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeShiftOverrideDurationNumber(coordinator, entry)])


class HomeShiftOverrideDurationNumber(NumberEntity, RestoreEntity):
    """Number entity controlling the manual override duration.

    When set to a value > 0, any manual day-mode change will block automatic
    calendar-driven updates for that many minutes.  Setting it to 0 disables
    the override mechanism entirely.
    """

    _attr_has_entity_name = True
    _attr_name = "Override Duration"

    _attr_native_min_value = 0
    _attr_native_max_value = 1440  # 24 h maximum
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-lock-outline"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{NUMBER_OVERRIDE_DURATION}"
        self._attr_native_value = float(coordinator.override_duration_minutes)

    async def async_added_to_hass(self) -> None:
        """Restore state from the previous run if available."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                restored = int(float(last_state.state))
                self._attr_native_value = float(restored)
                self._coordinator.set_override_duration_minutes(restored)
                _LOGGER.debug(
                    "Override duration restored to %d min from previous state",
                    restored,
                )
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float:
        """Return the current override duration in minutes."""
        return float(self._coordinator.override_duration_minutes)

    async def async_set_native_value(self, value: float) -> None:
        """Update the override duration."""
        minutes = int(value)
        self._coordinator.set_override_duration_minutes(minutes)
        self._attr_native_value = float(minutes)
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HomeShift",
            "manufacturer": "Gamso",
            "model": "HomeShift Controller",
        }
