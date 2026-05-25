"""Tests for HomeShiftCoordinator: ICS events, manual override, thermostat mode keys, scheduler refresh."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeshift.coordinator import HomeShiftCoordinator, MIDDAY_HOUR

from .conftest import (
    make_mock_hass,
    make_mock_entry,
    make_calendar_state,
)

try:
    from icalendar import Calendar
    HAS_ICALENDAR = True
except ImportError:
    Calendar = None  # type: ignore[assignment,misc]
    HAS_ICALENDAR = False

TELETRAVAIL_ICS = Path(__file__).parent.parent / "calendars" / "teletravail.ics"


# ---------------------------------------------------------------------------
# ICS half-day integration tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_ICALENDAR, reason="icalendar not installed")
class TestIcsHalfDayEvents:
    """Verify the teletravail ICS calendar contains the expected timed half-day events."""

    def test_has_timed_remote_events(self):
        """Has timed remote events."""
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
        """Has afternoon event."""
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
        """Has morning event."""
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
    """Basic text-level checks on the teletravail ICS file content."""

    def test_ics_contains_timed_events(self):
        """Ics contains timed events."""
        content = TELETRAVAIL_ICS.read_text()
        assert "DTSTART;TZID=" in content

    def test_ics_contains_afternoon_description(self):
        """Ics contains afternoon description."""
        content = TELETRAVAIL_ICS.read_text()
        assert "après-midi" in content.lower()

    def test_ics_contains_morning_description(self):
        """Ics contains morning description."""
        content = TELETRAVAIL_ICS.read_text()
        assert "matin" in content.lower()

    def test_ics_timed_event_count(self):
        """Ics timed event count."""
        content = TELETRAVAIL_ICS.read_text()
        count = content.count("DTSTART;TZID=")
        assert count >= 3


# ---------------------------------------------------------------------------
# Manual override duration
# ---------------------------------------------------------------------------

class TestManualOverrideDuration:
    """Verify that a manual override duration blocks automatic calendar-driven changes."""

    def test_override_blocks_auto_update(self):
        """After a manual change with override_duration=120, auto-update is blocked."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=120)
        coordinator = HomeShiftCoordinator(hass, entry)

        loop = asyncio.get_event_loop()
        base_time = datetime(2026, 3, 12, 9, 0, 0)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = base_time
            loop.run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        assert coordinator.override_until is not None

        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Vacances",
            start_time="2026-03-12 00:00:00",
            end_time="2026-03-13 00:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 0, 0)
            loop.run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Télétravail"

    def test_override_expiry_resumes_auto_update(self):
        """After the override expires, automatic mode changes resume."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=60)
        coordinator = HomeShiftCoordinator(hass, entry)

        loop = asyncio.get_event_loop()
        base_time = datetime(2026, 3, 12, 9, 0, 0)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = base_time
            loop.run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Vacances",
            start_time="2026-03-12 00:00:00",
            end_time="2026-03-13 00:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 10, 1, 0)
            loop.run_until_complete(coordinator.async_update_data())

        assert coordinator.override_until is None
        assert coordinator.day_mode == "Maison"

    def test_override_zero_does_not_block(self):
        """When override_duration is 0 (disabled), auto-update works immediately."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=0)
        coordinator = HomeShiftCoordinator(hass, entry)

        loop = asyncio.get_event_loop()

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 0, 0)
            loop.run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        assert coordinator.override_until is None

        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Vacances",
            start_time="2026-03-12 00:00:00",
            end_time="2026-03-13 00:00:00",
        )
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 5, 0)
            loop.run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Maison"

    def test_new_manual_change_resets_override_timer(self):
        """A second manual change resets (extends) the override deadline."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=60)
        coordinator = HomeShiftCoordinator(hass, entry)

        loop = asyncio.get_event_loop()
        first_time = datetime(2026, 3, 12, 9, 0, 0)
        second_time = datetime(2026, 3, 12, 9, 30, 0)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = first_time
            loop.run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        first_override = coordinator.override_until
        assert first_override is not None

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = second_time
            loop.run_until_complete(coordinator.async_set_day_mode("Travail"))

        second_override = coordinator.override_until
        assert second_override is not None
        assert second_override > first_override

    def test_override_until_appears_in_coordinator_data(self):
        """override_until is exposed in coordinator.data after a manual change."""
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(state="off")
        entry = make_mock_entry(override_duration=60)
        coordinator = HomeShiftCoordinator(hass, entry)

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coordinator.async_update_data())
        assert result.get("override_until") is None

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 0, 0)
            loop.run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        assert coordinator.data.get("override_until") is not None
        assert "2026-03-12" in coordinator.data["override_until"]

    def test_set_override_duration_via_setter_updates_runtime_value(self):
        """set_override_duration_minutes() changes the runtime override duration."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=0)
        coordinator = HomeShiftCoordinator(hass, entry)

        assert coordinator.override_duration_minutes == 0
        coordinator.set_override_duration_minutes(90)
        assert coordinator.override_duration_minutes == 90

    def test_runtime_override_duration_takes_effect_on_next_manual_change(self):
        """After set_override_duration_minutes(90), the next manual change uses 90 min."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=0)
        coordinator = HomeShiftCoordinator(hass, entry)

        loop = asyncio.get_event_loop()
        coordinator.set_override_duration_minutes(90)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 0, 0)
            loop.run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        assert coordinator.override_until is not None
        assert coordinator.override_until.minute == 30
        assert coordinator.override_until.hour == 10

    def test_set_override_duration_zero_clamps_correctly(self):
        """set_override_duration_minutes(0) is valid and disables the override."""
        hass = make_mock_hass()
        entry = make_mock_entry(override_duration=120)
        coordinator = HomeShiftCoordinator(hass, entry)

        coordinator.set_override_duration_minutes(0)
        assert coordinator.override_duration_minutes == 0

    def test_set_override_duration_negative_clamps_to_zero(self):
        """Negative values are clamped to 0."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        coordinator.set_override_duration_minutes(-5)
        assert coordinator.override_duration_minutes == 0


# ---------------------------------------------------------------------------
# Thermostat mode key resolution
# ---------------------------------------------------------------------------

class TestThermostatModeKeyResolution:
    """Verify thermostat_mode accepts display values AND internal keys."""

    def test_set_thermostat_mode_by_display_value(self):
        """Set thermostat mode by display value."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coordinator.async_set_thermostat_mode("Chauffage"))
        assert coordinator.thermostat_mode == "Chauffage"
        assert coordinator.thermostat_mode_key == "heating"

    def test_set_thermostat_mode_by_internal_key_exact_case(self):
        """Set thermostat mode by internal key exact case."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coordinator.async_set_thermostat_mode("heating"))
        assert coordinator.thermostat_mode == "Chauffage"
        assert coordinator.thermostat_mode_key == "heating"

    def test_set_thermostat_mode_by_internal_key_lowercase(self):
        """Set thermostat mode by internal key lowercase."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coordinator.async_set_thermostat_mode("heating"))
        assert coordinator.thermostat_mode == "Chauffage"

    def test_set_thermostat_mode_off_key(self):
        """Set thermostat mode off key."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coordinator.async_set_thermostat_mode("off"))
        assert coordinator.thermostat_mode == "Eteint"
        assert coordinator.thermostat_mode_key == "off"

    def test_set_thermostat_mode_unknown_rejected(self):
        """Set thermostat mode unknown rejected."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        initial = coordinator.thermostat_mode
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coordinator.async_set_thermostat_mode("unknown_mode"))
        assert coordinator.thermostat_mode == initial

    def test_thermostat_mode_key_in_coordinator_data(self):
        """Thermostat mode key in coordinator data."""
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coordinator.async_update_data())
        assert "thermostat_mode_key" in result
        assert result["thermostat_mode_key"] in ("off", "heating", "cooling", "ventilation")


# ---------------------------------------------------------------------------
# Scheduler refresh
# ---------------------------------------------------------------------------

class TestSchedulerRefresh:
    """Verify async_refresh_schedulers turns on/off the right switches."""

    def _hass(self):
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        hass.states.get.return_value = make_calendar_state(state="off")
        return hass

    def test_active_schedulers_turned_on_others_off(self):
        """Active schedulers turned on others off."""
        schedulers = {
            "Maison": ["switch.sched_maison"],
            "Travail": ["switch.sched_travail_a", "switch.sched_travail_b"],
            "Télétravail": ["switch.sched_teletravail"],
        }
        hass = self._hass()
        coordinator = HomeShiftCoordinator(
            hass, make_mock_entry(schedulers_per_mode=schedulers)
        )
        coordinator.day_mode = "Travail"

        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())

        calls = hass.services.async_call.call_args_list
        on_calls  = [c for c in calls if c.args[1] == "turn_on"]
        off_calls = [c for c in calls if c.args[1] == "turn_off"]

        assert len(on_calls) == 1
        assert set(on_calls[0].args[2]["entity_id"]) == {
            "switch.sched_travail_a",
            "switch.sched_travail_b",
        }
        assert len(off_calls) == 1
        assert set(off_calls[0].args[2]["entity_id"]) == {
            "switch.sched_maison",
            "switch.sched_teletravail",
        }

    def test_no_schedulers_configured_does_nothing(self):
        """No schedulers configured does nothing."""
        hass = self._hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry(schedulers_per_mode={}))
        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())
        hass.services.async_call.assert_not_called()

    def test_active_mode_with_no_switches_only_turns_off_others(self):
        """Active mode with no switches only turns off others."""
        schedulers = {
            "Maison": ["switch.sched_maison"],
            "Travail": [],
            "Télétravail": ["switch.sched_teletravail"],
        }
        hass = self._hass()
        coordinator = HomeShiftCoordinator(
            hass, make_mock_entry(schedulers_per_mode=schedulers)
        )
        coordinator.day_mode = "Travail"

        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())

        calls = hass.services.async_call.call_args_list
        on_calls  = [c for c in calls if c.args[1] == "turn_on"]
        off_calls = [c for c in calls if c.args[1] == "turn_off"]

        assert len(on_calls) == 0
        assert len(off_calls) == 1
        assert set(off_calls[0].args[2]["entity_id"]) == {
            "switch.sched_maison",
            "switch.sched_teletravail",
        }

    def test_shared_switch_not_turned_off(self):
        """Shared switch not turned off."""
        shared = "switch.shared"
        schedulers = {
            "Maison": [shared, "switch.maison_only"],
            "Travail": [shared],
        }
        hass = self._hass()
        coordinator = HomeShiftCoordinator(
            hass, make_mock_entry(schedulers_per_mode=schedulers)
        )
        coordinator.day_mode = "Travail"

        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())

        calls = hass.services.async_call.call_args_list
        off_calls = [c for c in calls if c.args[1] == "turn_off"]
        turned_off = set(off_calls[0].args[2]["entity_id"]) if off_calls else set()
        assert shared not in turned_off
        assert "switch.maison_only" in turned_off

    def test_mode_change_triggers_scheduler_refresh(self):
        """Mode change triggers scheduler refresh."""
        schedulers = {
            "Maison": ["switch.sched_maison"],
            "Télétravail": ["switch.sched_teletravail"],
        }
        hass = self._hass()
        coordinator = HomeShiftCoordinator(
            hass, make_mock_entry(schedulers_per_mode=schedulers)
        )

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 12, 9, 0, 0)
            asyncio.get_event_loop().run_until_complete(
                coordinator.async_set_day_mode("Télétravail")
            )

        on_calls = [
            c for c in hass.services.async_call.call_args_list
            if c.args[1] == "turn_on"
        ]
        assert any(
            "switch.sched_teletravail" in c.args[2]["entity_id"]
            for c in on_calls
        )

    def _make_tagged_state(self, tags: list[str]) -> MagicMock:
        """Return a mock state with the given scheduler tags."""
        state = MagicMock()
        state.attributes = {"tags": tags}
        return state

    def test_thermostat_heating_disables_cooling_scheduler(self):
        """When thermostat=Chauffage, scheduler tagged Climatisation is force-disabled
        even if it belongs to the active day mode."""
        # day_mode = Travail → all 3 schedulers are candidates for ON
        # Only the one tagged Climatisation should be forced OFF.
        schedulers = {
            "Travail": [
                "switch.sched_clim",  # tagged Climatisation
                "switch.sched_chauffage",  # tagged Chauffage
                "switch.sched_volet",  # tagged Travail only (no thermostat tag)
            ],
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()

        def _get_state(entity_id):
            tags_map = {
                "switch.sched_clim": ["Climatisation", "Travail"],
                "switch.sched_chauffage": ["Chauffage", "Travail"],
                "switch.sched_volet": ["Travail"],
            }
            return self._make_tagged_state(tags_map.get(entity_id, []))

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, make_mock_entry(schedulers_per_mode=schedulers))
        coordinator.day_mode = "Travail"
        asyncio.get_event_loop().run_until_complete(coordinator.async_set_thermostat_mode("Chauffage"))
        hass.services.async_call.reset_mock()

        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())

        calls = hass.services.async_call.call_args_list
        on_calls = [c for c in calls if c.args[1] == "turn_on"]
        off_calls = [c for c in calls if c.args[1] == "turn_off"]

        turned_on = set(on_calls[0].args[2]["entity_id"]) if on_calls else set()
        turned_off = set(off_calls[0].args[2]["entity_id"]) if off_calls else set()

        assert "switch.sched_clim" not in turned_on, "Climatisation scheduler must NOT be ON when thermostat=Chauffage"
        assert "switch.sched_chauffage" in turned_on, "Chauffage scheduler must be ON"
        assert "switch.sched_volet" in turned_on, "Non-thermostat scheduler must be ON (day mode)"
        assert "switch.sched_clim" in turned_off, "Climatisation scheduler must be force-disabled"

    def test_thermostat_off_disables_all_thermostat_tagged_schedulers(self):
        """When thermostat=Eteint, all schedulers with any thermostat tag are disabled."""
        schedulers = {
            "Travail": [
                "switch.sched_clim",
                "switch.sched_chauffage",
                "switch.sched_volet",
            ],
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()

        def _get_state(entity_id):
            tags_map = {
                "switch.sched_clim": ["Climatisation", "Travail"],
                "switch.sched_chauffage": ["Chauffage", "Travail"],
                "switch.sched_volet": ["Travail"],
            }
            return self._make_tagged_state(tags_map.get(entity_id, []))

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, make_mock_entry(schedulers_per_mode=schedulers))
        coordinator.day_mode = "Travail"
        asyncio.get_event_loop().run_until_complete(coordinator.async_set_thermostat_mode("off"))
        hass.services.async_call.reset_mock()

        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())

        calls = hass.services.async_call.call_args_list
        on_calls = [c for c in calls if c.args[1] == "turn_on"]
        off_calls = [c for c in calls if c.args[1] == "turn_off"]

        turned_on = set(on_calls[0].args[2]["entity_id"]) if on_calls else set()
        turned_off = set(off_calls[0].args[2]["entity_id"]) if off_calls else set()

        assert "switch.sched_clim" not in turned_on
        assert "switch.sched_chauffage" not in turned_on
        assert "switch.sched_volet" in turned_on, "Non-thermostat scheduler must stay ON"
        assert "switch.sched_clim" in turned_off
        assert "switch.sched_chauffage" in turned_off

    def test_no_thermostat_tag_scheduler_follows_day_mode_only(self):
        """A scheduler with no thermostat tag always follows day-mode rules regardless of
        the active thermostat mode."""
        schedulers = {
            "Travail": ["switch.sched_presence"],
            "Télétravail": ["switch.sched_teletravail"],
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()

        # Both schedulers have no thermostat tags
        hass.states.get.side_effect = lambda _: self._make_tagged_state([])

        coordinator = HomeShiftCoordinator(hass, make_mock_entry(schedulers_per_mode=schedulers))
        coordinator.day_mode = "Travail"
        asyncio.get_event_loop().run_until_complete(coordinator.async_set_thermostat_mode("Chauffage"))
        hass.services.async_call.reset_mock()

        asyncio.get_event_loop().run_until_complete(coordinator.async_refresh_schedulers())

        calls = hass.services.async_call.call_args_list
        on_calls = [c for c in calls if c.args[1] == "turn_on"]
        turned_on = set(on_calls[0].args[2]["entity_id"]) if on_calls else set()

        assert "switch.sched_presence" in turned_on


# ---------------------------------------------------------------------------
# State persistence (async_restore_state / _async_save_state)
# ---------------------------------------------------------------------------

class TestStatePersistence:
    """Verify coordinator persists and restores day_mode and thermostat_mode."""

    def _make_store(self, stored_data: dict | None) -> MagicMock:
        """Return a mock Store that returns stored_data on async_load."""
        store = MagicMock()
        store.async_load = AsyncMock(return_value=stored_data)
        store.async_save = AsyncMock()
        return store

    def test_restore_state_sets_day_mode_from_stored_key(self):
        """async_restore_state() maps stored day_mode_key to the correct display value."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        mock_store = self._make_store({"day_mode_key": "remote", "thermostat_mode_key": "off"})
        coordinator._store = mock_store

        asyncio.get_event_loop().run_until_complete(coordinator.async_restore_state())

        assert coordinator.day_mode == "Télétravail"

    def test_restore_state_sets_thermostat_mode_from_stored_key(self):
        """async_restore_state() maps stored thermostat_mode_key to the correct display value."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        mock_store = self._make_store({"day_mode_key": "work", "thermostat_mode_key": "heating"})
        coordinator._store = mock_store

        asyncio.get_event_loop().run_until_complete(coordinator.async_restore_state())

        assert coordinator.thermostat_mode == "Chauffage"
        assert coordinator.thermostat_mode_key == "heating"

    def test_restore_state_no_stored_data_uses_defaults(self):
        """async_restore_state() leaves defaults untouched when storage is empty."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        initial_day = coordinator.day_mode
        initial_thermo = coordinator.thermostat_mode
        mock_store = self._make_store(None)
        coordinator._store = mock_store

        asyncio.get_event_loop().run_until_complete(coordinator.async_restore_state())

        assert coordinator.day_mode == initial_day
        assert coordinator.thermostat_mode == initial_thermo

    def test_restore_state_unknown_key_ignored(self):
        """async_restore_state() ignores keys not present in the current mode map."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        initial_day = coordinator.day_mode
        mock_store = self._make_store({"day_mode_key": "unknown_key", "thermostat_mode_key": "off"})
        coordinator._store = mock_store

        asyncio.get_event_loop().run_until_complete(coordinator.async_restore_state())

        # Unknown day_mode_key is ignored; thermostat_mode key is still restored
        assert coordinator.day_mode == initial_day
        assert coordinator.thermostat_mode == "Eteint"

    def test_restore_state_handles_load_error_gracefully(self):
        """async_restore_state() does not raise when storage load fails."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        initial_day = coordinator.day_mode
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(side_effect=OSError("disk error"))
        coordinator._store = mock_store

        # Should not raise
        asyncio.get_event_loop().run_until_complete(coordinator.async_restore_state())
        assert coordinator.day_mode == initial_day

    def test_save_state_called_on_manual_day_mode_change(self):
        """_async_save_state() is awaited after async_set_day_mode()."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        mock_store = MagicMock()
        mock_store.async_save = AsyncMock()
        coordinator._store = mock_store

        asyncio.get_event_loop().run_until_complete(coordinator.async_set_day_mode("Télétravail"))

        mock_store.async_save.assert_called_once()
        saved = mock_store.async_save.call_args[0][0]
        assert saved["day_mode_key"] == "remote"

    def test_save_state_called_on_manual_thermostat_mode_change(self):
        """_async_save_state() is awaited after async_set_thermostat_mode()."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        mock_store = MagicMock()
        mock_store.async_save = AsyncMock()
        coordinator._store = mock_store

        asyncio.get_event_loop().run_until_complete(
            coordinator.async_set_thermostat_mode("Chauffage")
        )

        mock_store.async_save.assert_called_once()
        saved = mock_store.async_save.call_args[0][0]
        assert saved["thermostat_mode_key"] == "heating"

    def test_save_state_called_on_auto_mode_change(self):
        """_async_save_state() is awaited when auto-update changes day_mode."""
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-04 00:00:00",
            end_time="2026-03-05 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        coordinator.day_mode = "Maison"  # Start with a different mode
        mock_store = MagicMock()
        mock_store.async_save = AsyncMock()
        coordinator._store = mock_store

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 4, 10, 0, 0)  # Wednesday
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # Day mode should have changed (auto-update), triggering a save
        assert coordinator.day_mode == "Télétravail"
        mock_store.async_save.assert_called_once()


# ---------------------------------------------------------------------------
# Early switch tests
# ---------------------------------------------------------------------------

def _mock_get_events(calendar_entity: str, events: list[dict]):
    """Return an AsyncMock that simulates calendar.get_events returning `events`."""
    return AsyncMock(return_value={calendar_entity: {"events": events}})


class TestEarlySwitch:
    """Verify the early_switch_minutes feature pre-activates timed events."""

    def test_early_switch_activates_before_timed_event(self):
        """Calendar off; timed event starts in 90 min; early_switch=120 → mode switches now."""
        hass = make_mock_hass()
        entry = make_mock_entry(early_switch_minutes=120)
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T14:00:00", "end": "2026-03-11T18:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 12, 0, 0)  # 90 min before 14:00
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Télétravail"

    def test_early_switch_not_active_outside_window(self):
        """Event starts in 3h; early_switch=120 → still too far out, no pre-activation."""
        hass = make_mock_hass()
        entry = make_mock_entry(early_switch_minutes=120)
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T15:00:00", "end": "2026-03-11T18:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 12, 0, 0)  # 3 h before 15:00
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Travail"  # default, no early switch

    def test_early_switch_does_not_activate_for_allday_event(self):
        """All-day event (date-only start); early_switch=120 → no pre-activation."""
        hass = make_mock_hass()
        entry = make_mock_entry(early_switch_minutes=120)
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            # All-day event: start has no 'T' time separator
            [{"summary": "Télétravail", "start": "2026-03-12", "end": "2026-03-13"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 23, 0, 0)  # within 120 min of midnight → all-day ignored
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Travail"  # no early switch for all-day

    def test_early_switch_zero_no_effect(self):
        """early_switch=0 (disabled): timed event in 30 min, no pre-activation."""
        hass = make_mock_hass()
        entry = make_mock_entry(early_switch_minutes=0)
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T14:00:00", "end": "2026-03-11T18:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 13, 30, 0)  # 30 min before event
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.day_mode == "Travail"

    def test_next_mode_at_reflects_early_switch(self):
        """next_mode_at = event_start - early_switch_minutes for a timed event."""
        hass = make_mock_hass()
        entry = make_mock_entry(early_switch_minutes=120)
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T14:00:00", "end": "2026-03-11T18:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 9, 0, 0)  # before the early window
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # next_mode_at should be 14:00 - 120 min = 12:00
        assert coordinator.next_mode_at == datetime(2026, 3, 11, 12, 0, 0)
        assert coordinator.next_mode_predicted == "Télétravail"

    def test_next_mode_at_allday_not_shifted(self):
        """All-day event: next_mode_at is not shifted by early_switch."""
        hass = make_mock_hass()
        entry = make_mock_entry(early_switch_minutes=120)
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-13", "end": "2026-03-14"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        # Friday 10:00 — all-day event on Saturday; early switch should not shift it
        now = datetime(2026, 3, 13, 10, 0, 0)  # Saturday all-day event already active
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # All-day events start at midnight (parsed as 00:00:00 from date-only string)
        # The event is active now, so next change is when it ends (Sunday midnight)
        assert coordinator.next_mode_at is not None
        assert coordinator.next_mode_at.hour == 0 and coordinator.next_mode_at.minute == 0


# ---------------------------------------------------------------------------
# Cover heat control
# ---------------------------------------------------------------------------

class TestCoverHeatControl:
    """Verify CoverManager.async_check_heat_protection closes covers when conditions are met."""

    def _make_entry(self, cover_entities=None, temp_sensor="sensor.temp", threshold=30.0, time_start="08:00:00", time_end="20:00:00", cover_action=None, my_button=None):
        from custom_components.homeshift.const import (
            CONF_COVER_ENTITIES,
            CONF_COVER_TEMP_SENSOR,
            CONF_COVER_TEMP_THRESHOLD,
            CONF_COVER_TIME_START,
            CONF_COVER_TIME_END,
            CONF_COVER_ACTION,
            CONF_COVER_MY_BUTTON,
        )

        entry = make_mock_entry()
        entry.options = {
            CONF_COVER_ENTITIES: cover_entities or ["cover.volet_salon"],
            CONF_COVER_TEMP_SENSOR: temp_sensor,
            CONF_COVER_TEMP_THRESHOLD: threshold,
            CONF_COVER_TIME_START: time_start,
            CONF_COVER_TIME_END: time_end,
        }
        if cover_action is not None:
            entry.options[CONF_COVER_ACTION] = cover_action
        if my_button is not None:
            entry.options[CONF_COVER_MY_BUTTON] = my_button
        return entry

    def _temp_state(self, temperature: float):
        state = MagicMock()
        state.state = str(temperature)
        return state

    def test_close_cover_called_when_hot_and_in_window(self):
        """cover.close_cover is called by default when temperature > threshold inside the window."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(threshold=30.0, time_start="08:00:00", time_end="20:00:00")

        def _get_state(entity_id):
            if entity_id == "sensor.temp":
                return self._temp_state(35.0)
            return make_calendar_state(state="off")

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_check_heat_protection(now)
        )

        hass.services.async_call.assert_called_once()
        call = hass.services.async_call.call_args
        assert call.args[0] == "cover"
        assert call.args[1] == "close_cover"
        assert "cover.volet_salon" in call.args[2]["entity_id"]

    def test_stop_cover_called_when_configured_and_hot(self):
        """cover.stop_cover is called when configured explicitly and temperature > threshold."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(threshold=30.0, time_start="08:00:00", time_end="20:00:00", cover_action="stop_cover")

        def _get_state(entity_id):
            if entity_id == "sensor.temp":
                return self._temp_state(35.0)
            return make_calendar_state(state="off")

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_check_heat_protection(now)
        )

        hass.services.async_call.assert_called_once()
        call = hass.services.async_call.call_args
        assert call.args[0] == "cover"
        assert call.args[1] == "stop_cover"
        assert "cover.volet_salon" in call.args[2]["entity_id"]

    def test_my_position_button_pressed_when_configured_and_hot(self):
        """button.press is called on the My button entity when action=my_position and hot."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(
            threshold=30.0,
            time_start="08:00:00",
            time_end="20:00:00",
            cover_action="my_position",
            my_button="button.volet_salon_my_position",
        )

        def _get_state(entity_id):
            if entity_id == "sensor.temp":
                return self._temp_state(35.0)
            return make_calendar_state(state="off")

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(coordinator._cover_manager.async_check_heat_protection(now))

        hass.services.async_call.assert_called_once()
        call = hass.services.async_call.call_args
        assert call.args[0] == "button"
        assert call.args[1] == "press"
        assert call.args[2]["entity_id"] == "button.volet_salon_my_position"

    def test_my_position_no_call_when_button_not_configured(self):
        """No service call when action=my_position but no button entity is set."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(
            threshold=30.0,
            time_start="08:00:00",
            time_end="20:00:00",
            cover_action="my_position",  # no my_button
        )

        def _get_state(entity_id):
            if entity_id == "sensor.temp":
                return self._temp_state(35.0)
            return make_calendar_state(state="off")

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(coordinator._cover_manager.async_check_heat_protection(now))

        hass.services.async_call.assert_not_called()

    def test_no_call_when_below_threshold(self):
        """cover.stop_cover is NOT called when temperature is below threshold."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(threshold=30.0)

        def _get_state(entity_id):
            if entity_id == "sensor.temp":
                return self._temp_state(25.0)
            return make_calendar_state(state="off")

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_check_heat_protection(now)
        )

        hass.services.async_call.assert_not_called()

    def test_no_call_outside_time_window(self):
        """cover.stop_cover is NOT called when current time is outside the window."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(threshold=30.0, time_start="08:00:00", time_end="18:00:00")

        def _get_state(entity_id):
            if entity_id == "sensor.temp":
                return self._temp_state(35.0)
            return make_calendar_state(state="off")

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)
        # 19:00 — outside the 08:00–18:00 window
        now = datetime(2026, 7, 1, 19, 0, 0)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_check_heat_protection(now)
        )

        hass.services.async_call.assert_not_called()

    def test_no_call_when_no_cover_entities_configured(self):
        """cover.stop_cover is NOT called when no cover entities are configured."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        # No cover config: use plain entry without cover settings
        entry = make_mock_entry()

        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_check_heat_protection(now)
        )

        hass.services.async_call.assert_not_called()

    def test_no_call_when_temp_sensor_unavailable(self):
        """cover.stop_cover is NOT called when the temperature sensor is missing."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry(threshold=30.0)

        # Return None for the sensor
        hass.states.get.return_value = None

        coordinator = HomeShiftCoordinator(hass, entry)
        now = datetime(2026, 7, 1, 14, 0, 0)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_check_heat_protection(now)
        )

        hass.services.async_call.assert_not_called()


# ---------------------------------------------------------------------------
# is_heat_protection_active (binary sensor logic)
# ---------------------------------------------------------------------------

class TestIsHeatProtectionActive:
    """Verify CoverManager.is_heat_protection_active returns correct bool/None values."""

    def _make_entry(self, threshold=30.0, time_start="08:00:00", time_end="20:00:00"):
        from custom_components.homeshift.const import (
            CONF_COVER_ENTITIES, CONF_COVER_TEMP_SENSOR, CONF_COVER_TEMP_THRESHOLD,
            CONF_COVER_TIME_START, CONF_COVER_TIME_END,
        )
        entry = make_mock_entry()
        entry.options = {
            CONF_COVER_ENTITIES: ["cover.volet_salon"],
            CONF_COVER_TEMP_SENSOR: "sensor.temp",
            CONF_COVER_TEMP_THRESHOLD: threshold,
            CONF_COVER_TIME_START: time_start,
            CONF_COVER_TIME_END: time_end,
        }
        return entry

    def _temp_state(self, temperature: float):
        state = MagicMock()
        state.state = str(temperature)
        return state

    def test_returns_true_when_hot_and_in_window(self):
        """Returns True when temperature > threshold inside the window."""
        hass = make_mock_hass()
        hass.states.get.side_effect = lambda eid: self._temp_state(35.0) if eid == "sensor.temp" else make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._make_entry())

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 14, 0, 0))

        assert result is True

    def test_returns_false_when_cool_and_in_window(self):
        """Returns False when temperature <= threshold (within window)."""
        hass = make_mock_hass()
        hass.states.get.side_effect = lambda eid: self._temp_state(25.0) if eid == "sensor.temp" else make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._make_entry())

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 14, 0, 0))

        assert result is False

    def test_returns_false_when_outside_window(self):
        """Returns False when current time is outside the active window."""
        hass = make_mock_hass()
        hass.states.get.side_effect = lambda eid: self._temp_state(40.0) if eid == "sensor.temp" else make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._make_entry(time_start="08:00:00", time_end="18:00:00"))

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 19, 0, 0))

        assert result is False

    def test_returns_none_when_not_configured(self):
        """Returns None when no cover entities or temp sensor configured."""
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 14, 0, 0))

        assert result is None

    def test_returns_none_when_sensor_unavailable(self):
        """Returns None when the temperature sensor is not found in HA state."""
        hass = make_mock_hass()
        hass.states.get.return_value = None
        coordinator = HomeShiftCoordinator(hass, self._make_entry())

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 14, 0, 0))

        assert result is None

    def test_returns_none_when_sensor_has_invalid_state(self):
        """Returns None when temperature sensor state is not a number."""
        hass = make_mock_hass()
        bad_state = MagicMock()
        bad_state.state = "unavailable"
        hass.states.get.side_effect = lambda eid: bad_state if eid == "sensor.temp" else make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._make_entry())

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 14, 0, 0))

        assert result is None

    def test_exactly_at_threshold_returns_false(self):
        """Returns False when temperature == threshold (not strictly above)."""
        hass = make_mock_hass()
        hass.states.get.side_effect = lambda eid: self._temp_state(30.0) if eid == "sensor.temp" else make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, self._make_entry(threshold=30.0))

        result = coordinator._cover_manager.is_heat_protection_active(datetime(2026, 7, 1, 14, 0, 0))

        assert result is False


# ---------------------------------------------------------------------------
# Sunrise scheduler adjustment
# ---------------------------------------------------------------------------

class TestSunriseSchedulerAdjustment:
    """Verify async_adjust_sunrise_schedulers edits scheduler timeslots."""

    def _make_entry(self, schedulers=None, earliest="07:10:00"):
        from custom_components.homeshift.const import (
            CONF_SUNRISE_SCHEDULERS, CONF_SUNRISE_EARLIEST,
        )
        entry = make_mock_entry()
        entry.options = {
            CONF_SUNRISE_SCHEDULERS: schedulers or ["switch.schedule_volets"],
            CONF_SUNRISE_EARLIEST: earliest,
        }
        return entry

    def _sun_state(self, next_rising_iso: str):
        state = MagicMock()
        state.attributes = {"next_rising": next_rising_iso}
        return state

    def _scheduler_state(self, actions=None, entities=None):
        state = MagicMock()
        state.attributes = {
            "actions": actions or [{"service": "cover.open_cover"}],
            "entities": entities or ["cover.volet_salon"],
        }
        return state

    def test_scheduler_edit_called_with_sunrise_when_after_earliest(self):
        """scheduler.edit is called with sunrise time when sunrise > earliest."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()

        entry = self._make_entry(earliest="07:10:00")

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                # sunrise at 07:45 local
                return self._sun_state("2026-07-01T05:45:00+00:00")
            if entity_id == "switch.schedule_volets":
                return self._scheduler_state()
            return None

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            from datetime import timezone, timedelta as tdelta
            tz_paris = timezone(tdelta(hours=2))
            mock_dt.as_local.side_effect = lambda dt: dt.astimezone(tz_paris)
            asyncio.get_event_loop().run_until_complete(
                coordinator._cover_manager.async_adjust_sunrise_schedulers()
            )

        hass.services.async_call.assert_called_once()
        call = hass.services.async_call.call_args
        assert call.args[0] == "scheduler"
        assert call.args[1] == "edit"
        timeslots = call.args[2]["timeslots"]
        assert len(timeslots) == 1
        # sunrise 07:45 > earliest 07:10 → use sunrise
        assert timeslots[0]["start"] == "07:45"

    def test_scheduler_edit_called_with_earliest_when_sunrise_before(self):
        """scheduler.edit is called with earliest time when sunrise < earliest."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()

        entry = self._make_entry(earliest="07:10:00")

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                # sunrise at 06:30 local (before earliest 07:10)
                return self._sun_state("2026-03-01T05:30:00+00:00")
            if entity_id == "switch.schedule_volets":
                return self._scheduler_state()
            return None

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            from datetime import timezone, timedelta as tdelta
            tz_paris = timezone(tdelta(hours=1))
            mock_dt.as_local.side_effect = lambda dt: dt.astimezone(tz_paris)
            asyncio.get_event_loop().run_until_complete(
                coordinator._cover_manager.async_adjust_sunrise_schedulers()
            )

        hass.services.async_call.assert_called_once()
        call = hass.services.async_call.call_args
        timeslots = call.args[2]["timeslots"]
        # sunrise 06:30 < earliest 07:10 → use earliest
        assert timeslots[0]["start"] == "07:10"

    def test_no_call_when_no_sunrise_schedulers_configured(self):
        """scheduler.edit is NOT called when no sunrise schedulers are configured."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = make_mock_entry()  # no sunrise_schedulers in config

        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_adjust_sunrise_schedulers()
        )

        hass.services.async_call.assert_not_called()

    def test_no_call_when_sun_entity_missing(self):
        """scheduler.edit is NOT called when sun.sun entity is unavailable."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        entry = self._make_entry()

        hass.states.get.return_value = None

        coordinator = HomeShiftCoordinator(hass, entry)

        asyncio.get_event_loop().run_until_complete(
            coordinator._cover_manager.async_adjust_sunrise_schedulers()
        )

        hass.services.async_call.assert_not_called()

    def test_action_gets_entity_id_merged_in(self):
        """The entity_id from scheduler.entities[0] is merged into the action dict."""
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()

        entry = self._make_entry(earliest="06:00:00")

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                return self._sun_state("2026-07-01T04:30:00+00:00")
            if entity_id == "switch.schedule_volets":
                return self._scheduler_state(
                    actions=[{"service": "cover.open_cover", "data": {"position": 100}}],
                    entities=["cover.volet_salon"],
                )
            return None

        hass.states.get.side_effect = _get_state

        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            from datetime import timezone, timedelta as tdelta
            tz_paris = timezone(tdelta(hours=2))
            mock_dt.as_local.side_effect = lambda dt: dt.astimezone(tz_paris)
            asyncio.get_event_loop().run_until_complete(
                coordinator._cover_manager.async_adjust_sunrise_schedulers()
            )

        call = hass.services.async_call.call_args
        action = call.args[2]["timeslots"][0]["actions"][0]
        assert action.get("entity_id") == "cover.volet_salon"
        assert action.get("service") == "cover.open_cover"


# ---------------------------------------------------------------------------
# Next-mode timer scheduling
# ---------------------------------------------------------------------------

class TestNextModeTimerScheduling:
    """Verify that a one-shot timer is scheduled/cancelled at _next_mode_at."""

    def test_timer_scheduled_when_next_mode_at_is_set(self):
        """After async_update_data, a cancel function is stored when next_mode_at is set."""
        hass = make_mock_hass()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())

        future_time = datetime(2026, 3, 11, 18, 0, 0)
        cancel_mock = MagicMock()

        with (
            patch("custom_components.homeshift.coordinator.dt_util") as mock_dt,
            patch(
                "custom_components.homeshift.coordinator.async_track_point_in_time",
                return_value=cancel_mock,
            ) as mock_track,
        ):
            mock_dt.now.return_value = datetime(2026, 3, 11, 9, 0, 0)
            coordinator._next_mode_at = future_time
            coordinator._next_mode = "Maison"
            coordinator._schedule_next_mode_timer()

        mock_track.assert_called_once()
        assert coordinator._cancel_next_mode_timer is cancel_mock

    def test_previous_timer_cancelled_before_rescheduling(self):
        """Calling _schedule_next_mode_timer twice cancels the first timer."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())

        first_cancel = MagicMock()
        second_cancel = MagicMock()

        with patch(
            "custom_components.homeshift.coordinator.async_track_point_in_time",
            side_effect=[first_cancel, second_cancel],
        ):
            coordinator._next_mode_at = datetime(2026, 3, 11, 18, 0, 0)
            coordinator._schedule_next_mode_timer()
            assert coordinator._cancel_next_mode_timer is first_cancel

            coordinator._next_mode_at = datetime(2026, 3, 11, 19, 0, 0)
            coordinator._schedule_next_mode_timer()

        first_cancel.assert_called_once()
        assert coordinator._cancel_next_mode_timer is second_cancel

    def test_no_timer_scheduled_when_next_mode_at_is_none(self):
        """When _next_mode_at is None, _schedule_next_mode_timer does nothing."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        coordinator._next_mode_at = None

        with patch(
            "custom_components.homeshift.coordinator.async_track_point_in_time"
        ) as mock_track:
            coordinator._schedule_next_mode_timer()

        mock_track.assert_not_called()
        assert coordinator._cancel_next_mode_timer is None

    def test_cancel_clears_pending_timer(self):
        """async_cancel_next_mode_timer calls the cancel function and clears it."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())

        cancel_fn = MagicMock()
        coordinator._cancel_next_mode_timer = cancel_fn

        coordinator.async_cancel_next_mode_timer()

        cancel_fn.assert_called_once()
        assert coordinator._cancel_next_mode_timer is None

    def test_cancel_is_no_op_when_no_timer(self):
        """async_cancel_next_mode_timer is safe to call when no timer is pending."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        assert coordinator._cancel_next_mode_timer is None
        coordinator.async_cancel_next_mode_timer()  # must not raise
        assert coordinator._cancel_next_mode_timer is None

    def test_timer_fires_and_triggers_sync(self):
        """When the timer callback fires, async_sync_calendar is scheduled."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())

        captured_callbacks = []

        def _fake_track(h, cb, fire_at):
            captured_callbacks.append(cb)
            return MagicMock()

        coordinator._next_mode_at = datetime(2026, 3, 11, 18, 0, 0)
        coordinator._next_mode = "Maison"

        with patch(
            "custom_components.homeshift.coordinator.async_track_point_in_time",
            side_effect=_fake_track,
        ):
            coordinator._schedule_next_mode_timer()

        assert len(captured_callbacks) == 1

        # Simulate the timer firing
        hass.async_create_task = MagicMock()
        with patch.object(coordinator, "async_sync_calendar", new_callable=AsyncMock):
            captured_callbacks[0](datetime(2026, 3, 11, 18, 0, 0))

        hass.async_create_task.assert_called_once()
        assert coordinator._cancel_next_mode_timer is None
