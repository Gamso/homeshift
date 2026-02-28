"""Tests for the DayModeCoordinator.

These tests verify:
- _detect_event_period classifies events correctly
- _parse_event_mode_map parses event-to-mode mappings
- _parse_thermostat_mode_map parses thermostat mode mappings
- scan_interval configuration is respected
- Default and custom mode mappings work
- Configurable absence mode works
- Half-day transitions work correctly
- ICS calendar contains expected events
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.day_mode.coordinator import DayModeCoordinator, MIDDAY_HOUR
from custom_components.day_mode.const import (
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODES,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCAN_INTERVAL,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_DAY_MODES,
    DEFAULT_THERMOSTAT_MODE_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_EVENT_MODE_MAP,
    DEFAULT_MODE_ABSENCE,
    EVENT_NONE,
    EVENT_VACATION,
    EVENT_TELEWORK,
    EVENT_PERIOD_ALL_DAY,
    EVENT_PERIOD_MORNING,
    EVENT_PERIOD_AFTERNOON,
)

# Patch frame.report_usage globally so DataUpdateCoordinator can be instantiated
_FRAME_PATCH = patch(
    "homeassistant.helpers.frame.report_usage",
    new=lambda *a, **kw: None,
)
_FRAME_PATCH.start()


# ---------------------------------------------------------------------------
# _detect_event_period unit tests
# ---------------------------------------------------------------------------

class TestDetectEventPeriod:
    """Tests for _detect_event_period static method."""

    def test_all_day_event_midnight_to_midnight(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-03-03 00:00:00", "2026-03-04 00:00:00"
        )
        assert result == EVENT_PERIOD_ALL_DAY

    def test_all_day_event_multi_day(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-08-03 00:00:00", "2026-08-17 00:00:00"
        )
        assert result == EVENT_PERIOD_ALL_DAY

    def test_morning_event(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-03-12 08:00:00", "2026-03-12 12:00:00"
        )
        assert result == EVENT_PERIOD_MORNING

    def test_morning_event_ending_at_13(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-03-12 08:00:00", "2026-03-12 13:00:00"
        )
        assert result == EVENT_PERIOD_MORNING

    def test_afternoon_event(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-03-04 13:00:00", "2026-03-04 18:00:00"
        )
        assert result == EVENT_PERIOD_AFTERNOON

    def test_afternoon_event_starting_at_14(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-03-04 14:00:00", "2026-03-04 18:00:00"
        )
        assert result == EVENT_PERIOD_AFTERNOON

    def test_spanning_event_treated_as_all_day(self):
        result = DayModeCoordinator._detect_event_period(
            "2026-03-04 08:00:00", "2026-03-04 18:00:00"
        )
        assert result == EVENT_PERIOD_ALL_DAY

    def test_invalid_format_defaults_to_all_day(self):
        result = DayModeCoordinator._detect_event_period("invalid", "also-invalid")
        assert result == EVENT_PERIOD_ALL_DAY

    def test_none_values_default_to_all_day(self):
        result = DayModeCoordinator._detect_event_period(None, None)
        assert result == EVENT_PERIOD_ALL_DAY

    def test_empty_strings_default_to_all_day(self):
        result = DayModeCoordinator._detect_event_period("", "")
        assert result == EVENT_PERIOD_ALL_DAY


# ---------------------------------------------------------------------------
# _parse_event_mode_map unit tests
# ---------------------------------------------------------------------------

class TestParseEventModeMap:
    """Tests for _parse_event_mode_map static method."""

    def test_default_map(self):
        mapping = DayModeCoordinator._parse_event_mode_map(DEFAULT_EVENT_MODE_MAP)
        assert "vacances" in mapping
        assert "télétravail" in mapping

    def test_empty_string(self):
        assert DayModeCoordinator._parse_event_mode_map("") == {}

    def test_none_value(self):
        assert DayModeCoordinator._parse_event_mode_map(None) == {}

    def test_single_mapping(self):
        mapping = DayModeCoordinator._parse_event_mode_map("Meeting:Bureau")
        assert mapping == {"meeting": "Bureau"}

    def test_multiple_mappings(self):
        mapping = DayModeCoordinator._parse_event_mode_map("A:X, B:Y, C:Z")
        assert mapping == {"a": "X", "b": "Y", "c": "Z"}

    def test_whitespace_handling(self):
        mapping = DayModeCoordinator._parse_event_mode_map("  Foo : Bar  ,  Baz:Qux  ")
        assert mapping == {"foo": "Bar", "baz": "Qux"}

    def test_missing_colon_ignored(self):
        mapping = DayModeCoordinator._parse_event_mode_map("Good:Value, BadEntry, Also:OK")
        assert mapping == {"good": "Value", "also": "OK"}

    def test_empty_key_or_value_ignored(self):
        mapping = DayModeCoordinator._parse_event_mode_map(":Value, Key:, Good:OK")
        assert mapping == {"good": "OK"}


# ---------------------------------------------------------------------------
# _parse_thermostat_mode_map unit tests
# ---------------------------------------------------------------------------

class TestParseThermostatModeMap:
    """Tests for _parse_thermostat_mode_map static method."""

    def test_default_map(self):
        """Default map parses correctly with preserved key case."""
        mapping = DayModeCoordinator._parse_thermostat_mode_map(DEFAULT_THERMOSTAT_MODE_MAP)
        assert mapping == {
            "Off": "Eteint",
            "Heating": "Chauffage",
            "Cooling": "Climatisation",
            "Ventilation": "Ventilation",
        }

    def test_empty_string(self):
        assert DayModeCoordinator._parse_thermostat_mode_map("") == {}

    def test_none_value(self):
        assert DayModeCoordinator._parse_thermostat_mode_map(None) == {}

    def test_single_mapping(self):
        mapping = DayModeCoordinator._parse_thermostat_mode_map("Off:Éteint")
        assert mapping == {"Off": "Éteint"}

    def test_preserves_key_case(self):
        """Keys preserve their case (unlike _parse_event_mode_map)."""
        mapping = DayModeCoordinator._parse_thermostat_mode_map("Heating:Chauffage, COOLING:Clim")
        assert "Heating" in mapping
        assert "COOLING" in mapping

    def test_whitespace_handling(self):
        mapping = DayModeCoordinator._parse_thermostat_mode_map("  Off : Eteint  ,  Heat : Chaud  ")
        assert mapping == {"Off": "Eteint", "Heat": "Chaud"}

    def test_missing_colon_ignored(self):
        mapping = DayModeCoordinator._parse_thermostat_mode_map("Off:Eteint, BadEntry, Heat:Chaud")
        assert mapping == {"Off": "Eteint", "Heat": "Chaud"}

    def test_values_become_thermostat_modes(self):
        """Parsed values should become the thermostat_modes list."""
        hass = MagicMock()
        entry = _make_mock_entry()
        coordinator = DayModeCoordinator(hass, entry)
        assert coordinator.thermostat_modes == ["Eteint", "Chauffage", "Climatisation", "Ventilation"]

    def test_initial_thermostat_mode_is_first_value(self):
        """Initial thermostat mode should be the first display value."""
        hass = MagicMock()
        entry = _make_mock_entry()
        coordinator = DayModeCoordinator(hass, entry)
        assert coordinator.thermostat_mode == "Eteint"

    def test_custom_map_changes_options(self):
        """Custom map changes thermostat modes and initial value."""
        hass = MagicMock()
        entry = _make_mock_entry(thermostat_mode_map="Eco:Économique, Comfort:Confort")
        coordinator = DayModeCoordinator(hass, entry)
        assert coordinator.thermostat_modes == ["Économique", "Confort"]
        assert coordinator.thermostat_mode == "Économique"

    def test_thermostat_mode_map_property(self):
        """The thermostat_mode_map property returns the full mapping."""
        hass = MagicMock()
        entry = _make_mock_entry()
        coordinator = DayModeCoordinator(hass, entry)
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
    holiday_calendar: str = "",
    scan_interval: int = DEFAULT_SCAN_INTERVAL,
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
    }
    if mode_default is not None:
        entry.data[CONF_MODE_DEFAULT] = mode_default
    if mode_weekend is not None:
        entry.data[CONF_MODE_WEEKEND] = mode_weekend
    if mode_holiday is not None:
        entry.data[CONF_MODE_HOLIDAY] = mode_holiday
    if event_mode_map is not None:
        entry.data[CONF_EVENT_MODE_MAP] = event_mode_map
    if mode_absence is not None:
        entry.data[CONF_MODE_ABSENCE] = mode_absence
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

    def test_default_scan_interval(self):
        hass = MagicMock()
        entry = _make_mock_entry(scan_interval=DEFAULT_SCAN_INTERVAL)
        coordinator = DayModeCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(minutes=DEFAULT_SCAN_INTERVAL)

    def test_custom_scan_interval(self):
        hass = MagicMock()
        entry = _make_mock_entry(scan_interval=15)
        coordinator = DayModeCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(minutes=15)

    def test_invalid_scan_interval_falls_back(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        entry.data[CONF_SCAN_INTERVAL] = "not_a_number"
        coordinator = DayModeCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(minutes=DEFAULT_SCAN_INTERVAL)


# ---------------------------------------------------------------------------
# Default mode mapping tests
# ---------------------------------------------------------------------------

class TestDefaultModeMapping:

    def test_no_event_weekday_sets_default(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)  # Wednesday
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT
        assert coordinator.data is None or True  # first call

    def test_full_day_telework_sets_telework_mode(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == "Télétravail"
        assert result["next_day_type"] == EVENT_TELEWORK
        assert result["event_period"] == EVENT_PERIOD_ALL_DAY

    def test_afternoon_telework_active(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 14, 0, 0)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == "Télétravail"
        assert result["event_period"] == EVENT_PERIOD_AFTERNOON

    def test_afternoon_telework_morning_no_event(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT
        assert result["next_day_type"] == EVENT_NONE

    def test_morning_telework_active(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == "Télétravail"
        assert result["event_period"] == EVENT_PERIOD_MORNING

    def test_morning_telework_afternoon_reverts(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Télétravail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT

    def test_vacation_event(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Vacances",
            start_time="2026-08-03 00:00:00", end_time="2026-08-17 00:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 5, 10, 0, 0)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == "Maison"
        assert result["next_day_type"] == EVENT_VACATION

    def test_weekend_sets_weekend_mode(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)  # Saturday
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == DEFAULT_MODE_WEEKEND

    def test_absence_mode_not_overridden(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_ABSENCE

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == DEFAULT_MODE_ABSENCE

    def test_holiday_calendar(self):
        hass = MagicMock()
        entry = _make_mock_entry(holiday_calendar="calendar.jours_feries")

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return _make_calendar_state(state="off")
            if entity_id == "calendar.jours_feries":
                return _make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state

        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert coordinator._day_mode == DEFAULT_MODE_HOLIDAY

    def test_build_result_keys(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())

        assert "day_mode" in result
        assert "thermostat_mode" in result
        assert "next_day_type" in result
        assert "current_event" in result
        assert "event_period" in result


# ---------------------------------------------------------------------------
# Custom mode mapping tests
# ---------------------------------------------------------------------------

class TestCustomModeMapping:

    def test_custom_default_mode(self):
        hass = MagicMock()
        entry = _make_mock_entry(mode_default="Bureau")
        entry.data[CONF_DAY_MODES] = "Bureau, Maison, Télétravail, Absence"
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Bureau"

    def test_custom_weekend_mode(self):
        hass = MagicMock()
        entry = _make_mock_entry(mode_weekend="Repos")
        entry.data[CONF_DAY_MODES] = "Travail, Repos, Maison, Télétravail, Absence"
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Repos"

    def test_custom_holiday_mode(self):
        hass = MagicMock()
        entry = _make_mock_entry(holiday_calendar="calendar.jours_feries", mode_holiday="Ferie")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Ferie, Télétravail, Absence"

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return _make_calendar_state(state="off")
            if entity_id == "calendar.jours_feries":
                return _make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Ferie"

    def test_custom_event_mode_map(self):
        hass = MagicMock()
        entry = _make_mock_entry(event_mode_map="Formation:Bureau, Conférence:Bureau")
        entry.data[CONF_DAY_MODES] = "Travail, Bureau, Maison, Télétravail, Absence"
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Formation",
            start_time="2026-03-04 09:00:00", end_time="2026-03-04 17:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Bureau"

    def test_event_mode_map_case_insensitive(self):
        hass = MagicMock()
        entry = _make_mock_entry(event_mode_map="télétravail:Remote")
        entry.data[CONF_DAY_MODES] = "Travail, Remote, Maison, Absence"
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Remote"

    def test_unmapped_event_weekend(self):
        hass = MagicMock()
        entry = _make_mock_entry(event_mode_map="")
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="RandomEvent",
            start_time="2026-03-07 10:00:00", end_time="2026-03-07 12:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_WEEKEND

    def test_mode_not_in_day_modes_not_applied(self):
        hass = MagicMock()
        entry = _make_mock_entry(event_mode_map="Télétravail:NonExistent")
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Travail"

    def test_event_priority_over_weekend(self):
        hass = MagicMock()
        entry = _make_mock_entry(event_mode_map="Astreinte:Astreinte")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Astreinte, Télétravail, Absence"
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Astreinte",
            start_time="2026-03-07 00:00:00", end_time="2026-03-08 00:00:00",
        )
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Astreinte"

    def test_event_priority_over_holiday(self):
        hass = MagicMock()
        entry = _make_mock_entry(holiday_calendar="calendar.jours_feries", event_mode_map="Astreinte:Astreinte")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Astreinte, Télétravail, Absence"

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return _make_calendar_state(
                    state="on", message="Astreinte",
                    start_time="2026-05-01 00:00:00", end_time="2026-05-02 00:00:00",
                )
            if entity_id == "calendar.jours_feries":
                return _make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Travail"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Astreinte"


# ---------------------------------------------------------------------------
# Configurable absence mode tests
# ---------------------------------------------------------------------------

class TestConfigurableAbsenceMode:

    def test_default_absence_blocks_update(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_ABSENCE

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_ABSENCE

    def test_custom_absence_blocks_update(self):
        hass = MagicMock()
        entry = _make_mock_entry(mode_absence="Vacances Longues")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Vacances Longues, Télétravail"
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Vacances Longues"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Vacances Longues"

    def test_non_absence_allows_update(self):
        hass = MagicMock()
        entry = _make_mock_entry(mode_absence="Away")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Away, Télétravail, Absence"
        hass.states.get.return_value = _make_calendar_state(state="off")
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"

        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            import asyncio
            asyncio.get_event_loop().run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT

    def test_absence_skips_check_next_day(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_ABSENCE
        coordinator.async_refresh = AsyncMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(coordinator.async_check_next_day())
        coordinator.async_refresh.assert_not_called()

    def test_non_absence_runs_check_next_day(self):
        hass = MagicMock()
        entry = _make_mock_entry()
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = DEFAULT_MODE_DEFAULT
        coordinator.async_refresh = AsyncMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(coordinator.async_check_next_day())
        coordinator.async_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# Half-day transition sequences
# ---------------------------------------------------------------------------

class TestHalfDayTransitionSequence:

    def test_full_day_sequence_afternoon_telework(self):
        hass = MagicMock()
        entry = _make_mock_entry(scan_interval=60)
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"
        import asyncio
        loop = asyncio.get_event_loop()

        # 00:10 - no event
        hass.states.get.return_value = _make_calendar_state(state="off")
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 0, 10, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT

        # 09:00 - still no event
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT

        # 13:00 - afternoon event starts
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 13, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Télétravail"

        # 15:00 - still active
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 15, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Télétravail"

        # 18:00 - event ended
        hass.states.get.return_value = _make_calendar_state(state="off")
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 18, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT

    def test_full_day_sequence_morning_telework(self):
        hass = MagicMock()
        entry = _make_mock_entry(scan_interval=60)
        coordinator = DayModeCoordinator(hass, entry)
        coordinator._day_mode = "Maison"
        import asyncio
        loop = asyncio.get_event_loop()

        # 08:00 - morning event active
        hass.states.get.return_value = _make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 8, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Télétravail"

        # 10:00 - still active
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == "Télétravail"

        # 12:00 - event ended
        hass.states.get.return_value = _make_calendar_state(state="off")
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 12, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT

        # 14:00 - no event
        with patch("custom_components.day_mode.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            loop.run_until_complete(coordinator._async_update_data())
        assert coordinator._day_mode == DEFAULT_MODE_DEFAULT


# ---------------------------------------------------------------------------
# ICS calendar tests
# ---------------------------------------------------------------------------

try:
    from icalendar import Calendar
    HAS_ICALENDAR = True
except ImportError:
    HAS_ICALENDAR = False
    Calendar = None

from pathlib import Path
TELETRAVAIL_ICS = Path(__file__).parent.parent / "calendars" / "teletravail.ics"


@pytest.mark.skipif(not HAS_ICALENDAR, reason="icalendar library not installed")
class TestIcsHalfDayEvents:

    def test_has_timed_telework_events(self):
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [c for c in cal.walk() if c.name == "VEVENT"]
            timed = [
                ev for ev in events
                if "Télétravail" in str(ev.get("SUMMARY", ""))
                and hasattr(ev.get("DTSTART").dt, "hour")
            ]
            assert len(timed) >= 2

    def test_has_afternoon_event(self):
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [c for c in cal.walk() if c.name == "VEVENT"]
            afternoon = [
                ev for ev in events
                if "Télétravail" in str(ev.get("SUMMARY", ""))
                and hasattr(ev.get("DTSTART").dt, "hour")
                and ev.get("DTSTART").dt.hour >= MIDDAY_HOUR
            ]
            assert len(afternoon) >= 1

    def test_has_morning_event(self):
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [c for c in cal.walk() if c.name == "VEVENT"]
            morning = [
                ev for ev in events
                if "Télétravail" in str(ev.get("SUMMARY", ""))
                and hasattr(ev.get("DTSTART").dt, "hour")
                and ev.get("DTSTART").dt.hour < MIDDAY_HOUR
            ]
            assert len(morning) >= 1


class TestIcsHalfDayEventsBasic:

    def test_ics_contains_timed_events(self):
        content = TELETRAVAIL_ICS.read_text()
        assert "DTSTART;TZID=" in content

    def test_ics_contains_afternoon_description(self):
        content = TELETRAVAIL_ICS.read_text()
        assert "après-midi" in content.lower()

    def test_ics_contains_morning_description(self):
        content = TELETRAVAIL_ICS.read_text()
        assert "matin" in content.lower()

    def test_ics_timed_event_count(self):
        content = TELETRAVAIL_ICS.read_text()
        count = content.count("DTSTART;TZID=")
        assert count >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
