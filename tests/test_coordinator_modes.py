"""Tests for HomeShiftCoordinator: mode mapping, absence, half-day sequences, today-type persistence."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import patch

from custom_components.homeshift.coordinator import HomeShiftCoordinator
from custom_components.homeshift.const import CONF_DAY_MODES

from custom_components.homeshift.const import (
    EVENT_PERIOD_ALL_DAY,
    EVENT_PERIOD_AFTERNOON,
    EVENT_PERIOD_MORNING,
)
from .conftest import (
    EVENT_NONE,
    EVENT_TELEWORK,
    EVENT_VACATION,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_MODE_ABSENCE,
    make_mock_hass,
    make_mock_entry,
    make_calendar_state,
)


# ---------------------------------------------------------------------------
# Default mode mapping tests
# ---------------------------------------------------------------------------

class TestDefaultModeMapping:
    """Verify that the default mode mapping rules apply for standard day types and events."""

    def test_no_event_weekday_sets_default(self):
        """No event weekday sets default."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)  # Wednesday
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    def test_full_day_telework_sets_telework_mode(self):
        """Full day telework sets telework mode."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            result = asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Télétravail"
        assert result["today_type"] == EVENT_TELEWORK
        assert result["event_period"] == EVENT_PERIOD_ALL_DAY

    def test_afternoon_telework_active(self):
        """Afternoon telework active."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 14, 0, 0)
            result = asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Télétravail"
        assert result["event_period"] == EVENT_PERIOD_AFTERNOON

    def test_afternoon_telework_morning_no_event(self):
        """Afternoon telework morning no event."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            result = asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT
        assert result["today_type"] == EVENT_NONE

    def test_morning_telework_active(self):
        """Morning telework active."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            result = asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Télétravail"
        assert result["event_period"] == EVENT_PERIOD_MORNING

    def test_morning_telework_afternoon_reverts(self):
        """Morning telework afternoon reverts."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Télétravail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    def test_vacation_event(self):
        """Vacation event."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Vacances",
            start_time="2026-08-03 00:00:00", end_time="2026-08-17 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 5, 10, 0, 0)
            result = asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Maison"
        assert result["today_type"] == EVENT_VACATION

    def test_weekend_sets_weekend_mode(self):
        """Weekend sets weekend mode."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)  # Saturday
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == DEFAULT_MODE_WEEKEND

    def test_absence_mode_not_overridden(self):
        """Absence mode not overridden."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_ABSENCE

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == DEFAULT_MODE_ABSENCE

    def test_holiday_calendar(self):
        """Holiday calendar."""
        hass = make_mock_hass()
        entry = make_mock_entry(holiday_calendar="calendar.jours_feries")

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return make_calendar_state(state="off")
            if entity_id == "calendar.jours_feries":
                return make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == DEFAULT_MODE_HOLIDAY

    def test_build_result_keys(self):
        """Build result keys."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            result = asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert "day_mode" in result
        assert "thermostat_mode" in result
        assert "today_type" in result
        assert "current_event" in result
        assert "event_period" in result


# ---------------------------------------------------------------------------
# Custom mode mapping tests
# ---------------------------------------------------------------------------

class TestCustomModeMapping:
    """Verify that custom mode names in the config are used in place of defaults."""

    def test_custom_default_mode(self):
        """Custom default mode."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_default="Bureau")
        entry.data[CONF_DAY_MODES] = "Bureau, Maison, Télétravail, Absence"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Bureau"

    def test_custom_weekend_mode(self):
        """Custom weekend mode."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_weekend="Repos")
        entry.data[CONF_DAY_MODES] = "Travail, Repos, Maison, Télétravail, Absence"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Repos"

    def test_custom_holiday_mode(self):
        """Custom holiday mode."""
        hass = make_mock_hass()
        entry = make_mock_entry(holiday_calendar="calendar.jours_feries", mode_holiday="Ferie")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Ferie, Télétravail, Absence"

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return make_calendar_state(state="off")
            if entity_id == "calendar.jours_feries":
                return make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Ferie"

    def test_custom_event_mode_map(self):
        """Custom event mode map."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="Formation:Bureau, Conférence:Bureau")
        entry.data[CONF_DAY_MODES] = "Travail, Bureau, Maison, Télétravail, Absence"
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Formation",
            start_time="2026-03-04 09:00:00", end_time="2026-03-04 17:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Bureau"

    def test_event_mode_map_case_insensitive(self):
        """Event mode map case insensitive."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="télétravail:Remote")
        entry.data[CONF_DAY_MODES] = "Travail, Remote, Maison, Absence"
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Remote"

    def test_unmapped_event_weekend(self):
        """Unmapped event weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="")
        hass.states.get.return_value = make_calendar_state(
            state="on", message="RandomEvent",
            start_time="2026-03-07 10:00:00", end_time="2026-03-07 12:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_WEEKEND

    def test_mode_not_in_day_modes_not_applied(self):
        """Mode not in day modes not applied."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="Télétravail:NonExistent")
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Travail"

    def test_event_priority_over_weekend(self):
        """Event priority over weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="Astreinte:Astreinte")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Astreinte, Télétravail, Absence"
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Astreinte",
            start_time="2026-03-07 00:00:00", end_time="2026-03-08 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Astreinte"

    def test_event_priority_over_holiday(self):
        """Event priority over holiday."""
        hass = make_mock_hass()
        entry = make_mock_entry(
            holiday_calendar="calendar.jours_feries",
            event_mode_map="Astreinte:Astreinte",
        )
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Astreinte, Télétravail, Absence"

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return make_calendar_state(
                    state="on", message="Astreinte",
                    start_time="2026-05-01 00:00:00", end_time="2026-05-02 00:00:00",
                )
            if entity_id == "calendar.jours_feries":
                return make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Travail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Astreinte"


# ---------------------------------------------------------------------------
# Configurable absence mode tests
# ---------------------------------------------------------------------------

class TestConfigurableAbsenceMode:
    """Verify that setting the absence mode blocks automatic calendar-driven updates."""

    def test_default_absence_blocks_update(self):
        """Default absence blocks update."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_ABSENCE

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_ABSENCE

    def test_custom_absence_blocks_update(self):
        """Custom absence blocks update."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_absence="Vacances Longues")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Vacances Longues, Télétravail"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Vacances Longues"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Vacances Longues"

    def test_non_absence_allows_update(self):
        """Non absence allows update."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_absence="Away")
        entry.data[CONF_DAY_MODES] = "Travail, Maison, Away, Télétravail, Absence"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    def test_absence_skips_check_next_day(self):
        """Absence skips check next day."""
        from unittest.mock import AsyncMock
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_ABSENCE
        coordinator.async_refresh = AsyncMock()

        asyncio.get_event_loop().run_until_complete(coordinator.async_check_next_day())
        coordinator.async_refresh.assert_not_called()

    def test_non_absence_runs_check_next_day(self):
        """Non absence runs check next day."""
        from unittest.mock import AsyncMock
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = DEFAULT_MODE_DEFAULT
        coordinator.async_refresh = AsyncMock()

        asyncio.get_event_loop().run_until_complete(coordinator.async_check_next_day())
        coordinator.async_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# Half-day transition sequences
# ---------------------------------------------------------------------------

class TestHalfDayTransitionSequence:
    """Verify mode transitions across a full day with morning or afternoon half-day events."""

    def test_full_day_sequence_afternoon_telework(self):
        """Full day sequence afternoon telework."""
        hass = make_mock_hass()
        entry = make_mock_entry(scan_interval=60)
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"
        loop = asyncio.get_event_loop()

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 0, 10, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 13, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Télétravail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 15, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Télétravail"

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 18, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    def test_full_day_sequence_morning_telework(self):
        """Full day sequence morning telework."""
        hass = make_mock_hass()
        entry = make_mock_entry(scan_interval=60)
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.day_mode = "Maison"
        loop = asyncio.get_event_loop()

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 8, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Télétravail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == "Télétravail"

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 12, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT


# ---------------------------------------------------------------------------
# Today-type persistence tests
# ---------------------------------------------------------------------------

class TestTodayTypePersistence:
    """Verify that today_type in the result persists for the full day."""

    def test_today_type_persists_after_morning_event_ends(self):
        """Today type persists after morning event ends."""
        hass = make_mock_hass()
        entry = make_mock_entry(scan_interval=60)
        coordinator = HomeShiftCoordinator(hass, entry)
        loop = asyncio.get_event_loop()

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 8, 0, 0)
            result = loop.run_until_complete(coordinator.async_update_data())
        assert result["today_type"] == EVENT_TELEWORK

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            result = loop.run_until_complete(coordinator.async_update_data())
        assert result["today_type"] == EVENT_TELEWORK

    def test_today_type_persists_after_afternoon_event_ends(self):
        """Today type persists after afternoon event ends."""
        hass = make_mock_hass()
        entry = make_mock_entry(scan_interval=60)
        coordinator = HomeShiftCoordinator(hass, entry)
        loop = asyncio.get_event_loop()

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 13, 0, 0)
            result = loop.run_until_complete(coordinator.async_update_data())
        assert result["today_type"] == EVENT_TELEWORK

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 20, 0, 0)
            result = loop.run_until_complete(coordinator.async_update_data())
        assert result["today_type"] == EVENT_TELEWORK

    def test_today_type_resets_at_midnight(self):
        """Today type resets at midnight."""
        hass = make_mock_hass()
        entry = make_mock_entry(scan_interval=60)
        coordinator = HomeShiftCoordinator(hass, entry)
        loop = asyncio.get_event_loop()

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 0, 0)
            result = loop.run_until_complete(coordinator.async_update_data())
        assert result["today_type"] == EVENT_TELEWORK

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 13, 9, 0, 0)
            result = loop.run_until_complete(coordinator.async_update_data())
        assert result["today_type"] == EVENT_NONE

    def test_no_event_day_stays_none(self):
        """No event day stays none."""
        hass = make_mock_hass()
        entry = make_mock_entry(scan_interval=60)
        coordinator = HomeShiftCoordinator(hass, entry)
        loop = asyncio.get_event_loop()

        hass.states.get.return_value = make_calendar_state(state="off")
        for hour in [8, 12, 17]:
            with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 3, 4, hour, 0, 0)
                result = loop.run_until_complete(coordinator.async_update_data())
            assert result["today_type"] == EVENT_NONE
