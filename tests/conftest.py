"""Shared fixtures and helpers for HomeShift coordinator tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.homeshift.const import (
    CONF_CALENDAR_ENTITY,
    CONF_DAY_MODE_MAP,
    CONF_EVENT_MODE_MAP,
    CONF_HOLIDAY_CALENDAR,
    CONF_MODE_ABSENCE,
    CONF_MODE_DEFAULT,
    CONF_MODE_HOLIDAY,
    CONF_MODE_WEEKEND,
    CONF_OVERRIDE_DURATION,
    CONF_SCAN_INTERVAL,
    CONF_SCHEDULERS_PER_MODE,
    CONF_THERMOSTAT_MODE_MAP,
    DEFAULT_OVERRIDE_DURATION,
    DEFAULT_SCAN_INTERVAL,
    EVENT_NONE,
    LOCALIZED_DEFAULTS,
)

# Use French locale defaults for all tests
_FR = LOCALIZED_DEFAULTS["fr"]

# Parse the FR day mode map: "Home:Maison, Work:Travail, Remote:Télétravail, Absence:Absence"
_fr_day_map: dict[str, str] = {k.strip(): v.strip() for k, _, v in (p.partition(":") for p in _FR[CONF_DAY_MODE_MAP].split(","))}
# Parse the FR event map: "Vacances:Home, Télétravail:Remote"  → {lowercase_kw: key}
_fr_event_map_raw: dict[str, str] = {k.strip().lower(): v.strip() for k, _, v in (p.partition(":") for p in _FR[CONF_EVENT_MODE_MAP].split(","))}

# today_type values returned by the coordinator (lowercase event keywords from the FR map)
EVENT_REMOTE: str = next(k for k, v in _fr_event_map_raw.items() if v == "Remote")  # "télétravail"
EVENT_VACATION: str = next(k for k, v in _fr_event_map_raw.items() if v == "Home")  # "vacances"
# EVENT_NONE is the sentinel "None" from const
EVENT_NONE = EVENT_NONE  # re-export

# Display values (used for coordinator.day_mode assertions)
DEFAULT_DAY_MODES: list[str] = list(_fr_day_map.values())
DEFAULT_THERMOSTAT_MODE_MAP: str = _FR[CONF_THERMOSTAT_MODE_MAP]
DEFAULT_MODE_DEFAULT: str = _fr_day_map[_FR[CONF_MODE_DEFAULT]]  # key "Work" → "Travail"
DEFAULT_MODE_WEEKEND: str = _fr_day_map[_FR[CONF_MODE_WEEKEND]]  # key "Home"  → "Maison"
DEFAULT_MODE_HOLIDAY: str = _fr_day_map[_FR[CONF_MODE_HOLIDAY]]  # key "Home"  → "Maison"
DEFAULT_MODE_ABSENCE: str = _fr_day_map[_FR[CONF_MODE_ABSENCE]]  # key "Absence" → "Absence"
DEFAULT_EVENT_MODE_MAP: str = _FR[CONF_EVENT_MODE_MAP]

# Patch frame.report_usage globally so DataUpdateCoordinator can be instantiated
_FRAME_PATCH = patch(
    "homeassistant.helpers.frame.report_usage",
    new=lambda *a, **kw: None,
    create=True,
)
_FRAME_PATCH.start()


def make_mock_hass() -> MagicMock:
    """Return a MagicMock hass with language='fr' for get_localized_defaults."""
    hass = MagicMock()
    hass.config.language = "fr"
    return hass


def make_mock_entry(
    calendar_entity: str = "calendar.teletravail",
    holiday_calendar: str = "calendar.jours_feries",
    scan_interval: int = DEFAULT_SCAN_INTERVAL,
    override_duration: int = DEFAULT_OVERRIDE_DURATION,
    schedulers_per_mode: dict | None = None,
    mode_default: str | None = None,
    mode_weekend: str | None = None,
    mode_holiday: str | None = None,
    event_mode_map: str | None = None,
    mode_absence: str | None = None,
    thermostat_mode_map: str | None = None,
) -> MagicMock:
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_CALENDAR_ENTITY: calendar_entity,
        CONF_HOLIDAY_CALENDAR: holiday_calendar,
        CONF_DAY_MODE_MAP: _FR[CONF_DAY_MODE_MAP],
        CONF_THERMOSTAT_MODE_MAP: thermostat_mode_map or DEFAULT_THERMOSTAT_MODE_MAP,
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_OVERRIDE_DURATION: override_duration,
        CONF_SCHEDULERS_PER_MODE: schedulers_per_mode or {},
        CONF_MODE_DEFAULT: mode_default if mode_default is not None else _FR[CONF_MODE_DEFAULT],
        CONF_MODE_WEEKEND: mode_weekend if mode_weekend is not None else _FR[CONF_MODE_WEEKEND],
        CONF_MODE_HOLIDAY: mode_holiday if mode_holiday is not None else _FR[CONF_MODE_HOLIDAY],
        CONF_EVENT_MODE_MAP: event_mode_map if event_mode_map is not None else DEFAULT_EVENT_MODE_MAP,
        CONF_MODE_ABSENCE: mode_absence if mode_absence is not None else _FR[CONF_MODE_ABSENCE],
    }
    return entry


def make_calendar_state(
    state: str = "on",
    message: str = "",
    start_time: str = "",
    end_time: str = "",
) -> MagicMock:
    """Create a mock calendar entity state."""
    mock_state = MagicMock()
    mock_state.state = state
    mock_state.attributes = {
        "message": message,
        "start_time": start_time,
        "end_time": end_time,
    }
    return mock_state
