"""Diagnostics support for HomeShift."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import HomeShiftCoordinator


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return the configuration and the runtime state worth seeing in a bug report.

    Nothing here is secret: the configuration only holds entity ids, mode
    maps and times.
    """
    coordinator: HomeShiftCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    diagnostics: dict[str, Any] = {
        "entry": {
            "version": entry.version,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
    }
    if coordinator is None:
        return diagnostics

    manager = coordinator.cover_manager
    diagnostics["coordinator"] = {
        "last_update_success": coordinator.last_update_success,
        "data": coordinator.data,
        "day_mode_map": coordinator.day_mode_map,
        "thermostat_mode_map": coordinator.thermostat_mode_map,
        "override_duration_minutes": coordinator.override_duration_minutes,
        "early_switch_minutes": coordinator.early_switch_minutes,
    }
    diagnostics["covers"] = {
        "cover_open_time": manager.cover_open_time,
        "daily_close_time": manager.daily_close_time,
        "daily_close_trigger": manager.daily_close_trigger,
        "heat_window_start": manager.heat_window_start,
        "covers_left_open": manager.covers_left_open,
        "covers_left_open_date": manager.covers_left_open_date.isoformat() if manager.covers_left_open_date else None,
    }
    return diagnostics
