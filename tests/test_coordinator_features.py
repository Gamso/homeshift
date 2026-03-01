"""Tests for HomeShiftCoordinator: ICS events, manual override, thermostat mode keys, scheduler refresh."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
        assert coordinator.thermostat_mode_key == "Heating"

    def test_set_thermostat_mode_by_internal_key_exact_case(self):
        """Set thermostat mode by internal key exact case."""
        hass = make_mock_hass()
        coordinator = HomeShiftCoordinator(hass, make_mock_entry())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coordinator.async_set_thermostat_mode("Heating"))
        assert coordinator.thermostat_mode == "Chauffage"
        assert coordinator.thermostat_mode_key == "Heating"

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
        assert coordinator.thermostat_mode_key == "Off"

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
        assert result["thermostat_mode_key"] in ("Off", "Heating", "Cooling", "Ventilation")


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
