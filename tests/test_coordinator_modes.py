"""Tests for HomeShiftCoordinator: mode mapping, absence, half-day sequences, today-type persistence."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.homeshift.coordinator import HomeShiftCoordinator
from custom_components.homeshift.const import CONF_DAY_MODE_MAP, CONF_EVENT_MODE_MAP

from .conftest import (
    set_day_mode,
    EVENT_NONE,
    EVENT_REMOTE,
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

    async def test_no_event_weekday_sets_default(self):
        """No event weekday sets default."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)  # Wednesday
            await coordinator.async_update_data()

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    async def test_full_day_remote_sets_remote_mode(self):
        """Full day remote sets remote mode."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            result = await coordinator.async_update_data()

        assert coordinator.day_mode == "Télétravail"
        assert result["today_type"] == EVENT_REMOTE

    async def test_afternoon_remote_active(self):
        """Afternoon remote active."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 14, 0, 0)
            result = await coordinator.async_update_data()

        assert coordinator.day_mode == "Télétravail"

    async def test_afternoon_remote_morning_no_event(self):
        """Afternoon remote morning no event."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            result = await coordinator.async_update_data()

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT
        assert result["today_type"] == EVENT_NONE

    async def test_morning_remote_active(self):
        """Morning remote active."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            result = await coordinator.async_update_data()

        assert coordinator.day_mode == "Télétravail"

    async def test_morning_remote_afternoon_reverts(self):
        """Morning remote afternoon reverts."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Télétravail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            await coordinator.async_update_data()

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    async def test_vacation_event(self):
        """Vacation event."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Vacances",
            start_time="2026-08-03 00:00:00", end_time="2026-08-17 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 5, 10, 0, 0)
            result = await coordinator.async_update_data()

        assert coordinator.day_mode == "Maison"
        assert result["today_type"] == EVENT_VACATION

    async def test_weekend_sets_weekend_mode(self):
        """Weekend sets weekend mode."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)  # Saturday
            await coordinator.async_update_data()

        assert coordinator.day_mode == DEFAULT_MODE_WEEKEND

    async def test_absence_mode_not_overridden(self):
        """Absence mode not overridden."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_ABSENCE)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            await coordinator.async_update_data()

        assert coordinator.day_mode == DEFAULT_MODE_ABSENCE

    async def test_holiday_calendar(self):
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
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            await coordinator.async_update_data()

        assert coordinator.day_mode == DEFAULT_MODE_HOLIDAY

    async def test_build_result_keys(self):
        """Build result keys."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            result = await coordinator.async_update_data()

        assert "day_mode" in result
        assert "thermostat_mode" in result
        assert "today_type" in result
        assert "current_event" in result


# ---------------------------------------------------------------------------
# Custom mode mapping tests
# ---------------------------------------------------------------------------

class TestCustomModeMapping:
    """Verify that custom mode names in the config are used in place of defaults."""

    async def test_custom_default_mode(self):
        """Custom default mode."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_default="work")
        entry.data[CONF_DAY_MODE_MAP] = "work:Bureau, home:Maison, remote:Télétravail, away:Absence"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Bureau"

    async def test_custom_weekend_mode(self):
        """Custom weekend mode."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_weekend="home")
        entry.data[CONF_DAY_MODE_MAP] = "work:Travail, home:Repos, remote:Télétravail, away:Absence"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Repos"

    async def test_custom_holiday_mode(self):
        """Custom holiday mode."""
        hass = make_mock_hass()
        entry = make_mock_entry(holiday_calendar="calendar.jours_feries", mode_holiday="home")
        entry.data[CONF_DAY_MODE_MAP] = "work:Travail, home:Ferie, remote:Télétravail, away:Absence"

        def get_state(entity_id):
            if entity_id == "calendar.teletravail":
                return make_calendar_state(state="off")
            if entity_id == "calendar.jours_feries":
                return make_calendar_state(state="on")
            return None
        hass.states.get.side_effect = get_state
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Ferie"

    async def test_custom_event_mode_map(self):
        """Custom event mode map."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="Formation:work, Conférence:work")
        entry.data[CONF_DAY_MODE_MAP] = "work:Bureau, home:Maison, remote:Télétravail, away:Absence"
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Formation",
            start_time="2026-03-04 09:00:00", end_time="2026-03-04 17:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Bureau"

    async def test_event_mode_map_case_insensitive(self):
        """Event mode map case insensitive."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="télétravail:remote")
        entry.data[CONF_DAY_MODE_MAP] = "work:Travail, remote:Remote, home:Maison, away:Absence"
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Remote"

    async def test_unmapped_event_weekend(self):
        """Unmapped event weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="")
        hass.states.get.return_value = make_calendar_state(
            state="on", message="RandomEvent",
            start_time="2026-03-07 10:00:00", end_time="2026-03-07 12:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_WEEKEND

    async def test_mode_not_in_day_modes_not_applied(self):
        """Mode not in day modes not applied."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="Télétravail:NonExistent")
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-03 00:00:00", end_time="2026-03-04 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 3, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Travail"

    async def test_event_priority_over_weekend(self):
        """Event priority over weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry(event_mode_map="Astreinte:work")
        entry.data[CONF_DAY_MODE_MAP] = "work:Astreinte, home:Maison, remote:Télétravail, away:Absence"
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Astreinte",
            start_time="2026-03-07 00:00:00", end_time="2026-03-08 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Astreinte"

    async def test_event_priority_over_holiday(self):
        """Event priority over holiday."""
        hass = make_mock_hass()
        entry = make_mock_entry(
            holiday_calendar="calendar.jours_feries",
            event_mode_map="Astreinte:work",
        )
        entry.data[CONF_DAY_MODE_MAP] = "work:Astreinte, home:Maison, remote:Télétravail, away:Absence"

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
        set_day_mode(coordinator, "Travail")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 1, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Astreinte"


# ---------------------------------------------------------------------------
# Configurable absence mode tests
# ---------------------------------------------------------------------------

class TestConfigurableAbsenceMode:
    """Verify that setting the absence mode blocks automatic calendar-driven updates."""

    async def test_default_absence_blocks_update(self):
        """Default absence blocks update."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_ABSENCE)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_ABSENCE

    async def test_custom_absence_blocks_update(self):
        """Custom absence blocks update."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_absence="away")
        entry.data[CONF_DAY_MODE_MAP] = "work:Travail, home:Maison, away:Vacances Longues, remote:Télétravail"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Vacances Longues")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Vacances Longues"

    async def test_non_absence_allows_update(self):
        """Non absence allows update."""
        hass = make_mock_hass()
        entry = make_mock_entry(mode_absence="away", mode_default="work")
        entry.data[CONF_DAY_MODE_MAP] = "work:Travail, home:Maison, away:Away, remote:Télétravail"
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    async def test_absence_still_refreshes_on_sync_calendar(self):
        """Absence blocks the mode change, not the refresh itself.

        _async_update_data already leaves the day mode alone in absence mode;
        skipping the whole refresh also skipped the cover schedule, the
        next-mode prediction and the data broadcast, and made the
        homeshift.sync_calendar service silently do nothing.
        """
        from unittest.mock import AsyncMock
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_ABSENCE)
        coordinator.async_refresh = AsyncMock()

        await coordinator.async_sync_calendar()
        coordinator.async_refresh.assert_called_once()

    async def test_non_absence_runs_sync_calendar(self):
        """Non absence runs check next day."""
        from unittest.mock import AsyncMock
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, DEFAULT_MODE_DEFAULT)
        coordinator.async_refresh = AsyncMock()

        await coordinator.async_sync_calendar()
        coordinator.async_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# Half-day transition sequences
# ---------------------------------------------------------------------------

class TestHalfDayTransitionSequence:
    """Verify mode transitions across a full day with morning or afternoon half-day events."""

    async def test_full_day_sequence_afternoon_remote(self):
        """Full day sequence afternoon remote."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 0, 10, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 13, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Télétravail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 15, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Télétravail"

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 18, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    async def test_full_day_sequence_morning_remote(self):
        """Full day sequence morning remote."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        set_day_mode(coordinator, "Maison")

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 8, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Télétravail"

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == "Télétravail"

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 12, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            await coordinator.async_update_data()
        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT


# ---------------------------------------------------------------------------
# Today-type persistence tests
# ---------------------------------------------------------------------------

class TestTodayTypePersistence:
    """Verify that today_type in the result persists for the full day."""

    async def test_today_type_persists_after_morning_event_ends(self):
        """Today type persists after morning event ends."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 8, 0, 0)
            result = await coordinator.async_update_data()
        assert result["today_type"] == EVENT_REMOTE

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 14, 0, 0)
            result = await coordinator.async_update_data()
        assert result["today_type"] == EVENT_REMOTE

    async def test_today_type_persists_after_afternoon_event_ends(self):
        """Today type persists after afternoon event ends."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-04 13:00:00", end_time="2026-03-04 18:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 13, 0, 0)
            result = await coordinator.async_update_data()
        assert result["today_type"] == EVENT_REMOTE

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 20, 0, 0)
            result = await coordinator.async_update_data()
        assert result["today_type"] == EVENT_REMOTE

    async def test_today_type_resets_at_midnight(self):
        """Today type resets at midnight."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)

        hass.states.get.return_value = make_calendar_state(
            state="on", message="Télétravail",
            start_time="2026-03-12 08:00:00", end_time="2026-03-12 12:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 0, 0)
            result = await coordinator.async_update_data()
        assert result["today_type"] == EVENT_REMOTE

        hass.states.get.return_value = make_calendar_state(state="off")
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 13, 9, 0, 0)
            result = await coordinator.async_update_data()
        assert result["today_type"] == EVENT_NONE

    async def test_no_event_day_stays_none(self):
        """No event day stays none."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)

        hass.states.get.return_value = make_calendar_state(state="off")
        for hour in [8, 12, 17]:
            with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 3, 4, hour, 0, 0)
                result = await coordinator.async_update_data()
            assert result["today_type"] == EVENT_NONE
class TestCalendarDrivenAbsenceDoesNotFreezeTheIntegration:
    """Absence freezes automatic updates only when it was selected by hand.

    Mapping a calendar keyword to the absence mode used to be a one-way door:
    the event set the mode automatically, and from then on every automatic
    update was skipped — including the one that should have restored the
    normal mode once the event ended.
    """

    def _entry(self):
        entry = make_mock_entry(mode_absence="away", mode_default="work")
        entry.data[CONF_DAY_MODE_MAP] = "work:Travail, home:Maison, away:Absence, remote:Télétravail"
        entry.data[CONF_EVENT_MODE_MAP] = "Congés:away"
        return entry

    async def _run(self, coordinator, now):
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            await coordinator.async_update_data()

    async def test_event_sets_absence_then_the_end_of_the_event_restores_the_mode(self):
        hass = make_mock_hass()
        # Wednesday, an all-day "Congés" event is running
        hass.states.get.return_value = make_calendar_state(
            state="on", message="Congés",
            start_time="2026-03-04 00:00:00", end_time="2026-03-05 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, self._entry())
        set_day_mode(coordinator, "Travail")

        await self._run(coordinator, datetime(2026, 3, 4, 10, 0, 0))
        assert coordinator.day_mode == "Absence"  # set by the calendar

        # The event is over — the mode must be free to move again
        hass.states.get.return_value = make_calendar_state(state="off")
        await self._run(coordinator, datetime(2026, 3, 5, 10, 0, 0))
        assert coordinator.day_mode == "Travail"

    async def test_manual_absence_still_blocks_automatic_updates(self):
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._entry())
        coordinator.async_refresh_schedulers = AsyncMock()
        coordinator._async_save_state = AsyncMock()
        coordinator.async_set_updated_data = MagicMock()

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            await coordinator.async_set_day_mode("Absence")

        assert coordinator._absence_is_manual is True
        await self._run(coordinator, datetime(2026, 3, 4, 10, 0, 0))
        assert coordinator.day_mode == "Absence"

    async def test_leaving_absence_by_hand_clears_the_flag(self):
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._entry())
        coordinator.async_refresh_schedulers = AsyncMock()
        coordinator._async_save_state = AsyncMock()
        coordinator.async_set_updated_data = MagicMock()
        set_day_mode(coordinator, "Absence")

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 9, 0, 0)
            await coordinator.async_set_day_mode("Maison")

        assert coordinator._absence_is_manual is False

    async def test_flag_survives_a_restart(self):
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, self._entry())
        coordinator._store.async_load = AsyncMock(
            return_value={"day_mode_key": "away", "absence_is_manual": True}
        )

        await coordinator.async_restore_state()

        assert coordinator.day_mode == "Absence"
        assert coordinator._absence_is_manual is True

    async def test_legacy_payload_treats_persisted_absence_as_manual(self):
        """Before the flag existed, only a hand-picked absence could persist."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, self._entry())
        coordinator._store.async_load = AsyncMock(return_value={"day_mode_key": "away"})

        await coordinator.async_restore_state()

        assert coordinator._absence_is_manual is True

    async def test_legacy_payload_with_another_mode_leaves_the_flag_off(self):
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, self._entry())
        coordinator._store.async_load = AsyncMock(return_value={"day_mode_key": "home"})

        await coordinator.async_restore_state()

        assert coordinator._absence_is_manual is False


# ---------------------------------------------------------------------------
# Unreadable calendar (audit B2 / P4)
# ---------------------------------------------------------------------------

def _states(calendar=None, holiday=None):
    """Return a states.get side effect serving the work and holiday calendars."""
    calendar = calendar if calendar is not None else make_calendar_state(state="off")
    holiday = holiday if holiday is not None else make_calendar_state(state="off")

    def _get(entity_id):
        if entity_id == "calendar.teletravail":
            return None if calendar == "missing" else calendar
        if entity_id == "calendar.jours_feries":
            return None if holiday == "missing" else holiday
        return None

    return _get


class TestUnreadableCalendarKeepsTheMode:
    """A calendar that cannot be read says nothing about today: keep the mode."""

    def _coordinator(self, day_mode, side_effect):
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        hass.states.get.side_effect = side_effect
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        coordinator._day_mode = day_mode
        coordinator.async_refresh_schedulers = AsyncMock()
        return coordinator

    async def _poll(self, coordinator, now=datetime(2026, 3, 3, 10, 0, 0)):  # Tuesday
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            return await coordinator.async_update_data()

    async def test_unavailable_calendar_keeps_remote_work(self):
        """CalDAV down on a remote-work Tuesday: no switch to Work and back."""
        coordinator = self._coordinator("Télétravail", _states(calendar=make_calendar_state(state="unavailable")))

        await self._poll(coordinator)

        assert coordinator.day_mode == "Télétravail"
        coordinator.async_refresh_schedulers.assert_not_called()

    async def test_unknown_calendar_keeps_the_mode(self):
        coordinator = self._coordinator("Télétravail", _states(calendar=make_calendar_state(state="unknown")))

        await self._poll(coordinator)

        assert coordinator.day_mode == "Télétravail"

    async def test_missing_calendar_keeps_the_mode(self):
        coordinator = self._coordinator("Télétravail", _states(calendar="missing"))

        await self._poll(coordinator)

        assert coordinator.day_mode == "Télétravail"

    async def test_unavailable_holiday_calendar_keeps_the_mode(self):
        """A bank holiday must not turn into a work day because its calendar is down."""
        coordinator = self._coordinator(DEFAULT_MODE_HOLIDAY, _states(holiday=make_calendar_state(state="unavailable")))

        await self._poll(coordinator)

        assert coordinator.day_mode == DEFAULT_MODE_HOLIDAY

    async def test_calendar_absence_is_not_cancelled(self):
        """An absence set by a calendar event survives a calendar outage."""
        coordinator = self._coordinator(DEFAULT_MODE_ABSENCE, _states(calendar=make_calendar_state(state="unavailable")))
        coordinator._absence_is_manual = False

        await self._poll(coordinator)

        assert coordinator.day_mode == DEFAULT_MODE_ABSENCE

    async def test_the_mode_follows_the_calendar_again_once_it_answers(self):
        side = {"calendar": make_calendar_state(state="unavailable")}
        coordinator = self._coordinator("Télétravail", lambda e: _states(**side)(e))

        await self._poll(coordinator)
        side["calendar"] = make_calendar_state(state="off")
        await self._poll(coordinator, datetime(2026, 3, 3, 10, 5, 0))

        assert coordinator.day_mode == DEFAULT_MODE_DEFAULT

    async def test_the_outage_is_warned_about_once(self, caplog):
        coordinator = self._coordinator("Télétravail", _states(calendar=make_calendar_state(state="unavailable")))

        with caplog.at_level("WARNING"):
            await self._poll(coordinator)
            await self._poll(coordinator, datetime(2026, 3, 3, 10, 5, 0))

        warnings = [r for r in caplog.records if "Calendar unreadable" in r.getMessage() and r.levelname == "WARNING"]
        assert len(warnings) == 1


class TestCoversDoNotWaitForTheCalendar:
    """The cover schedule runs even when the calendar cannot be read (audit P4)."""

    def _coordinator(self, side_effect):
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        hass.states.get.side_effect = side_effect
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        coordinator._day_mode = DEFAULT_MODE_DEFAULT
        coordinator.async_refresh_schedulers = AsyncMock()
        manager = coordinator._cover_manager
        manager.async_compute_daily_schedule = AsyncMock()
        manager.async_check_daily_schedule = AsyncMock()
        manager.async_check_heat_protection = AsyncMock()
        coordinator._schedule_cover_timers = MagicMock()
        return coordinator

    async def _poll(self, coordinator, now):
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            await coordinator.async_update_data()

    async def test_covers_are_scheduled_and_checked_without_the_calendar(self):
        coordinator = self._coordinator(_states(calendar="missing"))

        await self._poll(coordinator, datetime(2026, 3, 3, 8, 0, 0))

        manager = coordinator._cover_manager
        manager.async_compute_daily_schedule.assert_awaited_once()
        manager.async_check_daily_schedule.assert_awaited_once()
        manager.async_check_heat_protection.assert_awaited_once()

    async def test_a_provisional_schedule_is_computed_again_once_the_calendar_answers(self):
        side = {"calendar": "missing"}
        coordinator = self._coordinator(lambda e: _states(**side)(e))

        await self._poll(coordinator, datetime(2026, 3, 3, 0, 1, 0))
        await self._poll(coordinator, datetime(2026, 3, 3, 0, 6, 0))
        assert coordinator._cover_manager.async_compute_daily_schedule.await_count == 1

        side["calendar"] = make_calendar_state(state="off")
        await self._poll(coordinator, datetime(2026, 3, 3, 0, 11, 0))
        await self._poll(coordinator, datetime(2026, 3, 3, 0, 16, 0))
        assert coordinator._cover_manager.async_compute_daily_schedule.await_count == 2
