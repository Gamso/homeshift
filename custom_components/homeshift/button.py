"""Button platform for HomeShift integration — open/close the covers on demand."""
from __future__ import annotations

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON_CLOSE_COVERS, BUTTON_OPEN_COVERS, CONF_DAILY_COVER_ITEMS, DOMAIN
from .coordinator import HomeShiftCoordinator
from .entity import async_remove_stale_entities, setup_entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover buttons, only when the daily schedule drives covers.

    Same condition as the cover open/close time sensors.
    """
    coordinator: HomeShiftCoordinator = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **entry.options}
    if not config.get(CONF_DAILY_COVER_ITEMS):
        async_remove_stale_entities(hass, entry, BUTTON_DOMAIN, [BUTTON_OPEN_COVERS, BUTTON_CLOSE_COVERS])
        return
    async_add_entities(
        [
            HomeShiftOpenCoversButton(coordinator, entry),
            HomeShiftCloseCoversButton(coordinator, entry),
        ]
    )


class HomeShiftOpenCoversButton(ButtonEntity):
    """Open every daily-schedule cover now, whatever the time or the mode.

    A plain button rather than a coordinator entity: it stays available
    while the coordinator is failing, and a failed cover command is logged
    without making it unavailable either.
    """

    _attr_icon = "mdi:window-shutter-open"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._coordinator = coordinator
        setup_entity(self, entry, BUTTON_DOMAIN, BUTTON_OPEN_COVERS)

    async def async_press(self) -> None:
        """Open the covers."""
        await self._coordinator.async_open_covers()


class HomeShiftCloseCoversButton(ButtonEntity):
    """Close every daily-schedule cover now, the way the evening close does.

    Open-window safety and My position buttons apply as they do at the
    scheduled close.
    """

    _attr_icon = "mdi:window-shutter"

    def __init__(self, coordinator: HomeShiftCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._coordinator = coordinator
        setup_entity(self, entry, BUTTON_DOMAIN, BUTTON_CLOSE_COVERS)

    async def async_press(self) -> None:
        """Close the covers."""
        await self._coordinator.async_close_covers()
