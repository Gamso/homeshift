"""Shared fixtures and helpers for HomeShift coordinator tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.homeshift.const import (
    CONF_CALENDAR_ENTITY,
    CONF_DAY_MODES,
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
    KEY_EVENT_NONE,
    KEY_EVENT_REMOTE,
    KEY_EVENT_VACATION,
    LOCALIZED_DEFAULTS,
)

# Use French locale defaults for all tests
_FR = LOCALIZED_DEFAULTS["fr"]
EVENT_NONE: str = _FR[KEY_EVENT_NONE]
EVENT_VACATION: str = _FR[KEY_EVENT_VACATION]
EVENT_REMOTE: str = _FR[KEY_EVENT_REMOTE]
DEFAULT_DAY_MODES: list[str] = [m.strip() for m in _FR[CONF_DAY_MODES].split(",")]
DEFAULT_THERMOSTAT_MODE_MAP: str = _FR[CONF_THERMOSTAT_MODE_MAP]
DEFAULT_MODE_DEFAULT: str = _FR[CONF_MODE_DEFAULT]
DEFAULT_MODE_WEEKEND: str = _FR[CONF_MODE_WEEKEND]
DEFAULT_MODE_HOLIDAY: str = _FR[CONF_MODE_HOLIDAY]
DEFAULT_EVENT_MODE_MAP: str = _FR[CONF_EVENT_MODE_MAP]
DEFAULT_MODE_ABSENCE: str = _FR[CONF_MODE_ABSENCE]

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
        CONF_DAY_MODES: ", ".join(DEFAULT_DAY_MODES),
        CONF_THERMOSTAT_MODE_MAP: thermostat_mode_map or DEFAULT_THERMOSTAT_MODE_MAP,
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_OVERRIDE_DURATION: override_duration,
        CONF_SCHEDULERS_PER_MODE: schedulers_per_mode or {},
        CONF_MODE_DEFAULT: mode_default if mode_default is not None else DEFAULT_MODE_DEFAULT,
        CONF_MODE_WEEKEND: mode_weekend if mode_weekend is not None else DEFAULT_MODE_WEEKEND,
        CONF_MODE_HOLIDAY: mode_holiday if mode_holiday is not None else DEFAULT_MODE_HOLIDAY,
        CONF_EVENT_MODE_MAP: event_mode_map if event_mode_map is not None else DEFAULT_EVENT_MODE_MAP,
        CONF_MODE_ABSENCE: mode_absence if mode_absence is not None else DEFAULT_MODE_ABSENCE,
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
