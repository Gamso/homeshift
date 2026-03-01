"""Tests for the HomeShiftCoordinator — static utilities and scan interval configuration.

These tests cover:
- detect_event_period classifies events correctly
- parse_event_mode_map parses event-to-mode mappings
- parse_thermostat_mode_map parses thermostat mode mappings
- scan_interval configuration is respected

Mode mapping, absence, half-day transitions and feature tests live in:
- tests/test_coordinator_modes.py
- tests/test_coordinator_features.py
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from custom_components.homeshift.coordinator import HomeShiftCoordinator
from custom_components.homeshift.const import (
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODE_MAP,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCAN_INTERVAL,
    CONF_OVERRIDE_DURATION,
    CONF_SCHEDULERS_PER_MODE,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_OVERRIDE_DURATION,
    EVENT_PERIOD_ALL_DAY,
    EVENT_PERIOD_MORNING,
    EVENT_PERIOD_AFTERNOON,
    LOCALIZED_DEFAULTS,
)

# Use French locale defaults for all tests
_FR = LOCALIZED_DEFAULTS["fr"]
_fr_day_map: dict[str, str] = {k.strip(): v.strip() for k, _, v in (p.partition(":") for p in _FR[CONF_DAY_MODE_MAP].split(","))}
_fr_event_map_raw: dict[str, str] = {k.strip().lower(): v.strip() for k, _, v in (p.partition(":") for p in _FR[CONF_EVENT_MODE_MAP].split(","))}
EVENT_REMOTE: str = next(k for k, v in _fr_event_map_raw.items() if v == "Remote")
EVENT_VACATION: str = next(k for k, v in _fr_event_map_raw.items() if v == "Home")
DEFAULT_DAY_MODES: list[str] = list(_fr_day_map.values())
DEFAULT_THERMOSTAT_MODE_MAP: str = _FR[CONF_THERMOSTAT_MODE_MAP]
DEFAULT_MODE_DEFAULT: str = _fr_day_map[_FR[CONF_MODE_DEFAULT]]
DEFAULT_MODE_WEEKEND: str = _fr_day_map[_FR[CONF_MODE_WEEKEND]]
DEFAULT_MODE_HOLIDAY: str = _fr_day_map[_FR[CONF_MODE_HOLIDAY]]
DEFAULT_EVENT_MODE_MAP: str = _FR[CONF_EVENT_MODE_MAP]
DEFAULT_MODE_ABSENCE: str = _fr_day_map[_FR[CONF_MODE_ABSENCE]]

# Patch frame.report_usage globally so DataUpdateCoordinator can be instantiated
_FRAME_PATCH = patch(
    "homeassistant.helpers.frame.report_usage",
    new=lambda *a, **kw: None,
    create=True,
)
_FRAME_PATCH.start()


def _make_mock_hass() -> MagicMock:
    """Return a MagicMock hass with language='fr' for get_localized_defaults."""
    hass = MagicMock()
    hass.config.language = "fr"
    return hass


# ---------------------------------------------------------------------------
# detect_event_period unit tests
# ---------------------------------------------------------------------------

class TestDetectEventPeriod:
    """Tests for detect_event_period static method."""

    def test_all_day_event_midnight_to_midnight(self):
        """All day event midnight to midnight."""
        result = HomeShiftCoordinator.detect_event_period("2026-03-03 00:00:00", "2026-03-04 00:00:00")
        assert result == EVENT_PERIOD_ALL_DAY

    def test_all_day_event_multi_day(self):
        """All day event multi day."""
        result = HomeShiftCoordinator.detect_event_period("2026-08-03 00:00:00", "2026-08-17 00:00:00")
        assert result == EVENT_PERIOD_ALL_DAY

    def test_morning_event(self):
        """Morning event."""
        result = HomeShiftCoordinator.detect_event_period("2026-03-12 08:00:00", "2026-03-12 12:00:00")
        assert result == EVENT_PERIOD_MORNING

    def test_morning_event_ending_at_13(self):
        """Morning event ending at 13."""
        result = HomeShiftCoordinator.detect_event_period("2026-03-12 08:00:00", "2026-03-12 13:00:00")
        assert result == EVENT_PERIOD_MORNING

    def test_afternoon_event(self):
        """Afternoon event."""
        result = HomeShiftCoordinator.detect_event_period("2026-03-04 13:00:00", "2026-03-04 18:00:00")
        assert result == EVENT_PERIOD_AFTERNOON

    def test_afternoon_event_starting_at_14(self):
        """Afternoon event starting at 14."""
        result = HomeShiftCoordinator.detect_event_period("2026-03-04 14:00:00", "2026-03-04 18:00:00")
        assert result == EVENT_PERIOD_AFTERNOON

    def test_spanning_event_treated_as_all_day(self):
        """Spanning event treated as all day."""
        result = HomeShiftCoordinator.detect_event_period("2026-03-04 08:00:00", "2026-03-04 18:00:00")
        assert result == EVENT_PERIOD_ALL_DAY

    def test_invalid_format_defaults_to_all_day(self):
        """Invalid format defaults to all day."""
        result = HomeShiftCoordinator.detect_event_period("invalid", "also-invalid")
        assert result == EVENT_PERIOD_ALL_DAY

    def test_none_values_default_to_all_day(self):
        """None values default to all day."""
        result = HomeShiftCoordinator.detect_event_period(None, None)
        assert result == EVENT_PERIOD_ALL_DAY

    def test_empty_strings_default_to_all_day(self):
        """Empty strings default to all day."""
        result = HomeShiftCoordinator.detect_event_period("", "")
        assert result == EVENT_PERIOD_ALL_DAY


# ---------------------------------------------------------------------------
# parse_event_mode_map unit tests
# ---------------------------------------------------------------------------

class TestParseEventModeMap:
    """Tests for parse_event_mode_map static method."""

    def test_default_map(self):
        """Default map."""
        mapping = HomeShiftCoordinator.parse_event_mode_map(DEFAULT_EVENT_MODE_MAP)
        assert "vacances" in mapping
        assert "télétravail" in mapping

    def test_empty_string(self):
        """Empty string."""
        assert not HomeShiftCoordinator.parse_event_mode_map("")

    def test_none_value(self):
        """None value."""
        assert not HomeShiftCoordinator.parse_event_mode_map(None)

    def test_single_mapping(self):
        """Single mapping."""
        mapping = HomeShiftCoordinator.parse_event_mode_map("Meeting:Bureau")
        assert mapping == {"meeting": "Bureau"}

    def test_multiple_mappings(self):
        """Multiple mappings."""
        mapping = HomeShiftCoordinator.parse_event_mode_map("A:X, B:Y, C:Z")
        assert mapping == {"a": "X", "b": "Y", "c": "Z"}

    def test_whitespace_handling(self):
        """Whitespace handling."""
        mapping = HomeShiftCoordinator.parse_event_mode_map("  Foo : Bar  ,  Baz:Qux  ")
        assert mapping == {"foo": "Bar", "baz": "Qux"}

    def test_missing_colon_ignored(self):
        """Missing colon ignored."""
        mapping = HomeShiftCoordinator.parse_event_mode_map("Good:Value, BadEntry, Also:OK")
        assert mapping == {"good": "Value", "also": "OK"}

    def test_empty_key_or_value_ignored(self):
        """Empty key or value ignored."""
        mapping = HomeShiftCoordinator.parse_event_mode_map(":Value, Key:, Good:OK")
        assert mapping == {"good": "OK"}


# ---------------------------------------------------------------------------
# parse_thermostat_mode_map unit tests
# ---------------------------------------------------------------------------

class TestParseThermostatModeMap:
    """Tests for parse_thermostat_mode_map static method."""

    def test_default_map(self):
        """Default map parses correctly with preserved key case."""
        mapping = HomeShiftCoordinator.parse_thermostat_mode_map(DEFAULT_THERMOSTAT_MODE_MAP)
        assert mapping == {
            "Off": "Eteint",
            "Heating": "Chauffage",
            "Cooling": "Climatisation",
            "Ventilation": "Ventilation",
        }

    def test_empty_string(self):
        """Empty string."""
        assert not HomeShiftCoordinator.parse_thermostat_mode_map("")

    def test_none_value(self):
        """None value."""
        assert not HomeShiftCoordinator.parse_thermostat_mode_map(None)

    def test_single_mapping(self):
        """Single mapping."""
        mapping = HomeShiftCoordinator.parse_thermostat_mode_map("Off:Éteint")
        assert mapping == {"Off": "Éteint"}

    def test_preserves_key_case(self):
        """Keys preserve their case (unlike parse_event_mode_map)."""
        mapping = HomeShiftCoordinator.parse_thermostat_mode_map("Heating:Chauffage, COOLING:Clim")
        assert "Heating" in mapping
        assert "COOLING" in mapping

    def test_whitespace_handling(self):
        """Whitespace handling."""
        mapping = HomeShiftCoordinator.parse_thermostat_mode_map("  Off : Eteint  ,  Heat : Chaud  ")
        assert mapping == {"Off": "Eteint", "Heat": "Chaud"}

    def test_missing_colon_ignored(self):
        """Missing colon ignored."""
        mapping = HomeShiftCoordinator.parse_thermostat_mode_map("Off:Eteint, BadEntry, Heat:Chaud")
        assert mapping == {"Off": "Eteint", "Heat": "Chaud"}

    def test_values_become_thermostat_modes(self):
        """Parsed values should become the thermostat_modes list."""
        hass = _make_mock_hass()
        entry = _make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.thermostat_modes == ["Eteint", "Chauffage", "Climatisation", "Ventilation"]

    def test_initial_thermostat_mode_is_first_value(self):
        """Initial thermostat mode should be the first display value."""
        hass = _make_mock_hass()
        entry = _make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.thermostat_mode == "Eteint"

    def test_custom_map_changes_options(self):
        """Custom map changes thermostat modes and initial value."""
        hass = _make_mock_hass()
        entry = _make_mock_entry(thermostat_mode_map="Eco:Économique, Comfort:Confort")
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.thermostat_modes == ["Économique", "Confort"]
        assert coordinator.thermostat_mode == "Économique"

    def test_thermostat_mode_map_property(self):
        """The thermostat_mode_map property returns the full mapping."""
        hass = _make_mock_hass()
        entry = _make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.thermostat_mode_map == {
            "Off": "Eteint",
            "Heating": "Chauffage",
            "Cooling": "Climatisation",
            "Ventilation": "Ventilation",
        }


# ---------------------------------------------------------------------------
# Helper to create a mock coordinator for integration-level tests
# ---------------------------------------------------------------------------


def _make_mock_entry(
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


def _make_calendar_state(
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


# ---------------------------------------------------------------------------
# Scan interval configuration tests
# ---------------------------------------------------------------------------

class TestScanIntervalConfig:
    """Tests for scan interval configuration on HomeShiftCoordinator."""

    def test_default_scan_interval(self):
        """Default scan interval."""
        hass = _make_mock_hass()
        entry = _make_mock_entry(scan_interval=DEFAULT_SCAN_INTERVAL)
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(minutes=DEFAULT_SCAN_INTERVAL)

    def test_custom_scan_interval(self):
        """Custom scan interval."""
        hass = _make_mock_hass()
        entry = _make_mock_entry(scan_interval=15)
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(minutes=15)

    def test_invalid_scan_interval_falls_back(self):
        """Invalid scan interval falls back."""
        hass = _make_mock_hass()
        entry = _make_mock_entry()
        entry.data[CONF_SCAN_INTERVAL] = "not_a_number"
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(minutes=DEFAULT_SCAN_INTERVAL)
