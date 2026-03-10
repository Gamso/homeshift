"""Tests for HomeShift sensor entities and coordinator timing properties.

Covers:
- next_mode_predicted / next_mode_at for: morning event, afternoon event,
  all-day event, no event (weekday and Friday→weekend transition)
- Sensor entity classes mirror the coordinator values
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from custom_components.homeshift.coordinator import HomeShiftCoordinator, MIDDAY_HOUR
from custom_components.homeshift.sensor import (
    HomeShiftNextModeSensor,
    HomeShiftNextModeAtSensor,
)

from .conftest import (
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    EVENT_REMOTE,
    make_mock_hass,
    make_mock_entry,
    make_calendar_state,
)


def _mock_get_events(calendar_entity: str, events: list[dict]):
    """Return an AsyncMock for hass.services.async_call that returns `events` for `calendar_entity`."""
    return AsyncMock(return_value={calendar_entity: {"events": events}})



# ---------------------------------------------------------------------------
# next_mode / next_mode_at — no event
# ---------------------------------------------------------------------------

class TestNextModeNoEvent:
    """next_mode_* when no calendar event is active."""

    def test_next_mode_none_before_first_update(self):
        """next_mode_predicted and next_mode_at are None before any update."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)
        assert coordinator.next_mode_predicted is None
        assert coordinator.next_mode_at is None

    def test_tuesday_evening_no_event_next_mode_is_weekend(self):
        """Tuesday 18:15, no event: next mode change is Saturday midnight (weekend).

        With a 7-day look-ahead window, Monday–Wednesday correctly surface the
        upcoming weekend rather than returning None for next_mode_at.
        """
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        # Tuesday March 10 18:15 — no events, but Saturday March 14 is in the
        # 7-day window → next change is Saturday midnight (weekend mode).
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 10, 18, 15, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_predicted == DEFAULT_MODE_WEEKEND
        assert coordinator.next_mode_at == datetime(2026, 3, 14, 0, 0, 0)

    def test_weekday_no_event_next_mode_is_weekend(self):
        """Thursday, no event: first mode CHANGE in the 2-day window is Saturday (weekend)."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        # Thursday March 5 — next change is Saturday midnight → weekend mode
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 5, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_predicted == DEFAULT_MODE_WEEKEND

    def test_friday_no_event_next_mode_is_weekend(self):
        """Friday, no event: tomorrow is Saturday → next predicted mode is weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        # Friday March 6
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 6, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_predicted == DEFAULT_MODE_WEEKEND

    def test_no_event_next_mode_at_is_tomorrow_midnight(self):
        """Friday, no event: next mode CHANGE is tomorrow (Saturday) at 00:00:00 — weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        # Friday March 6 — overnight → Saturday (weekend) is the first change
        now = datetime(2026, 3, 6, 14, 30, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_at == datetime(2026, 3, 7, 0, 0, 0)


# ---------------------------------------------------------------------------
# next_mode / next_mode_at — morning event
# ---------------------------------------------------------------------------

class TestNextModeMorningEvent:
    """next_mode_* with an active morning timed event."""

    def test_morning_event_next_mode_at_is_midday(self):
        """Morning event: next_mode_at is today at MIDDAY_HOUR:00:00."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-07 08:00:00",
            end_time="2026-03-07 13:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 7, 10, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        expected_midday = now.replace(hour=MIDDAY_HOUR, minute=0, second=0, microsecond=0)
        assert coordinator.next_mode_at == expected_midday

    def test_morning_event_weekday_next_mode_is_default(self):
        """After a morning remote event ends at midday on a Thursday, next mode is default."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        work_state = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-05 08:00:00",
            end_time="2026-03-05 13:00:00",
        )
        holiday_off = make_calendar_state(state="off")
        hass.states.get.side_effect = lambda eid: work_state if eid == "calendar.teletravail" else holiday_off
        coordinator = HomeShiftCoordinator(hass, entry)

        # Thursday at 10:00
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 5, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_predicted == DEFAULT_MODE_DEFAULT


# ---------------------------------------------------------------------------
# next_mode / next_mode_at — afternoon event
# ---------------------------------------------------------------------------

class TestNextModeAfternoonEvent:
    """next_mode_* with an active afternoon timed event."""

    def test_afternoon_event_next_mode_at_is_event_end(self):
        """Afternoon event: next_mode_at is the event's end time."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-07 13:00:00",
            end_time="2026-03-07 17:30:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 7, 14, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # tzinfo matches now (None in tests)
        expected = datetime(2026, 3, 7, 17, 30, 0, tzinfo=now.tzinfo)
        assert coordinator.next_mode_at == expected

    def test_afternoon_event_weekday_next_mode_is_default(self):
        """After an afternoon event ends on a weekday, predicted mode is default."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        work_state = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-05 13:00:00",
            end_time="2026-03-05 17:30:00",
        )
        holiday_off = make_calendar_state(state="off")
        hass.states.get.side_effect = lambda eid: work_state if eid == "calendar.teletravail" else holiday_off
        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 5, 14, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_predicted == DEFAULT_MODE_DEFAULT


# ---------------------------------------------------------------------------
# next_mode / next_mode_at — all-day event
# ---------------------------------------------------------------------------

class TestNextModeAllDayEvent:
    """next_mode_* with an active all-day event."""

    def test_all_day_event_next_mode_at_is_tomorrow_midnight(self):
        """All-day event: next_mode_at is tomorrow at 00:00:00."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-07 00:00:00",
            end_time="2026-03-08 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 7, 10, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_at == datetime(2026, 3, 8, 0, 0, 0)

    def test_all_day_friday_event_next_mode_is_weekend(self):
        """All-day event on Friday: tomorrow is Saturday → next predicted mode is weekend."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-06 00:00:00",
            end_time="2026-03-07 00:00:00",
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        # Friday March 6
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 6, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_predicted == DEFAULT_MODE_WEEKEND


# ---------------------------------------------------------------------------
# Sensor entity classes
# ---------------------------------------------------------------------------

class TestSensorEntities:
    """Sensor entity classes mirror coordinator values correctly."""

    def test_next_mode_sensor_returns_coordinator_value(self):
        """HomeShiftNextModeSensor.native_value == coordinator.next_mode_predicted."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 5, 10, 0, 0)  # Thursday
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        sensor = HomeShiftNextModeSensor(coordinator, entry)
        assert sensor.native_value == coordinator.next_mode_predicted

    def test_next_mode_at_sensor_returns_coordinator_value(self):
        """HomeShiftNextModeAtSensor.native_value == coordinator.next_mode_at."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        coordinator = HomeShiftCoordinator(hass, entry)

        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 7, 10, 0, 0)
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        sensor = HomeShiftNextModeAtSensor(coordinator, entry)
        assert sensor.native_value == coordinator.next_mode_at

    def test_sensor_unique_ids_are_distinct(self):
        """Each sensor has a distinct unique_id."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        coordinator = HomeShiftCoordinator(hass, entry)

        s1 = HomeShiftNextModeSensor(coordinator, entry)
        s2 = HomeShiftNextModeAtSensor(coordinator, entry)

        ids = {s1.unique_id, s2.unique_id}
        assert len(ids) == 2  # all distinct


# ---------------------------------------------------------------------------
# next_mode / next_mode_at — upcoming events (calendar currently off)
# ---------------------------------------------------------------------------


class TestNextModeUpcomingEvents:
    """next_mode_* when the calendar is off but future events exist today.

    This covers the main user scenario: at 8h, the calendar is 'off', but
    there is an afternoon Télétravail event at 14h. The sensors should
    predict that mode and that time.
    """

    def test_workday_morning_upcoming_afternoon_remote_event(self):
        """At 8h on a Wednesday, calendar off, Télétravail 14-18h today.
        next_mode = 'Télétravail', next_mode_at = 14:00.
        """
        hass = make_mock_hass()
        entry = make_mock_entry()
        # Calendar is currently off (no active event at 8h)
        hass.states.get.return_value = make_calendar_state(state="off")
        # Inject an upcoming afternoon event via calendar.get_events
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T14:00:00", "end": "2026-03-11T18:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 8, 0, 0)  # Wednesday
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # The French locale maps "télétravail" keyword → "Télétravail" display
        from .conftest import _fr_day_map, _FR
        from custom_components.homeshift.const import CONF_DAY_MODE_MAP

        remote_display = _fr_day_map["remote"]  # "Télétravail"
        assert coordinator.next_mode_predicted == remote_display
        assert coordinator.next_mode_at == datetime(2026, 3, 11, 14, 0, 0)

    def test_no_upcoming_events_next_change_is_weekend(self):
        """Calendar off, no upcoming mapped events on a Friday → next change is Saturday midnight."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        # get_events returns nothing
        hass.services.async_call = _mock_get_events("calendar.teletravail", [])
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 13, 8, 0, 0)  # Friday — next change is Saturday
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        assert coordinator.next_mode_at == datetime(2026, 3, 14, 0, 0, 0)

    def test_upcoming_event_with_tz_aware_start(self):
        """calendar.get_events returns tz-aware ISO string — should still be parsed."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T14:00:00+01:00", "end": "2026-03-11T18:00:00+01:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 8, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        from .conftest import _fr_day_map

        assert coordinator.next_mode_predicted == _fr_day_map["remote"]
        # Parsed datetime will have tzinfo from the ISO string
        assert coordinator.next_mode_at is not None
        assert coordinator.next_mode_at.hour == 14

    def test_upcoming_event_without_keyword_match_is_ignored(self):
        """Upcoming event that doesn't match any keyword: first mode change is Saturday midnight."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Réunion client", "start": "2026-03-13T15:00:00", "end": "2026-03-13T16:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 13, 8, 0, 0)  # Friday
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # No keyword match → first change is Saturday midnight (weekend)
        assert coordinator.next_mode_at == datetime(2026, 3, 14, 0, 0, 0)

    def test_get_events_service_unavailable_falls_back_gracefully(self):
        """If calendar.get_events is unavailable, next_mode_at still finds the next change (Saturday)."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        # Default MagicMock: await will raise TypeError, caught silently → upcoming=[]
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 13, 8, 0, 0)  # Friday
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # No events fetched → next change is Saturday midnight (weekend)
        assert coordinator.next_mode_at == datetime(2026, 3, 14, 0, 0, 0)


# ---------------------------------------------------------------------------
# next_mode — morning event + upcoming afternoon event
# ---------------------------------------------------------------------------


class TestNextModeMorningThenAfternoon:
    """When a morning event is active, check for a mapped afternoon event after midday."""

    def test_morning_remote_then_afternoon_remote_next_change_is_event_end(self):
        """Morning Télétravail active (8h-13h); an afternoon Télétravail follows at 14h.
        The FIRST mode change is when the morning event ends at 13h → mode reverts to Travail.
        next_mode = 'Travail', next_mode_at = 13:00.
        """
        hass = make_mock_hass()
        entry = make_mock_entry()
        work_state = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-11 08:00:00",
            end_time="2026-03-11 13:00:00",
        )
        holiday_off = make_calendar_state(state="off")
        hass.states.get.side_effect = lambda eid: work_state if eid == "calendar.teletravail" else holiday_off
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-11T14:00:00", "end": "2026-03-11T18:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 10, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        # At 13:00 the morning event ends: mode reverts to default (Travail)
        assert coordinator.next_mode_predicted == DEFAULT_MODE_DEFAULT
        assert coordinator.next_mode_at == datetime(2026, 3, 11, 13, 0, 0)

    def test_morning_remote_no_afternoon_event_returns_midday(self):
        """Morning Télétravail active; no afternoon mapped event → next_mode_at = midday."""
        hass = make_mock_hass()
        entry = make_mock_entry()
        work_state = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-11 08:00:00",
            end_time="2026-03-11 13:00:00",
        )
        holiday_off = make_calendar_state(state="off")
        hass.states.get.side_effect = lambda eid: work_state if eid == "calendar.teletravail" else holiday_off
        hass.services.async_call = _mock_get_events("calendar.teletravail", [])
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 10, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        expected_midday = now.replace(hour=MIDDAY_HOUR, minute=0, second=0, microsecond=0)
        assert coordinator.next_mode_at == expected_midday


# ---------------------------------------------------------------------------
# next_mode — cross-day (N events / tomorrow's all-day event)
# ---------------------------------------------------------------------------


class TestNextModeCrossDay:
    """General algorithm scenarios: cross-midnight and multiple events per day."""

    def test_tomorrow_allday_event_detected_at_night(self):
        """At 01:00, calendar off (today is Travail), tomorrow has all-day Télétravail.
        The general algorithm should find tomorrow midnight as the first change point
        where mode becomes Télétravail.
        """
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        # All-day event tomorrow (Friday): Télétravail
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [{"summary": "Télétravail", "start": "2026-03-06T00:00:00", "end": "2026-03-07T00:00:00"}],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        # Thursday 01:00 — calendar off, no event for today
        now = datetime(2026, 3, 5, 1, 0, 0)
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        from .conftest import _fr_day_map

        # next change: Friday midnight → Télétravail all-day event starts
        assert coordinator.next_mode_predicted == _fr_day_map["remote"]
        assert coordinator.next_mode_at == datetime(2026, 3, 6, 0, 0, 0)

    def test_multiple_events_per_day_finds_first_change(self):
        """Three events today: Télétravail 10-12, Télétravail 14-16, Vacances 17-18.
        At 09:00 (mode=Travail, calendar off), first change is at 10:00 → Télétravail.
        """
        hass = make_mock_hass()
        entry = make_mock_entry()
        hass.states.get.return_value = make_calendar_state(state="off")
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [
                {"summary": "Télétravail", "start": "2026-03-11T10:00:00", "end": "2026-03-11T12:00:00"},
                {"summary": "Télétravail", "start": "2026-03-11T14:00:00", "end": "2026-03-11T16:00:00"},
                {"summary": "Vacances", "start": "2026-03-11T17:00:00", "end": "2026-03-11T18:00:00"},
            ],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 9, 0, 0)  # Wednesday 09:00
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        from .conftest import _fr_day_map

        # First change: 10:00 when Télétravail event starts
        assert coordinator.next_mode_predicted == _fr_day_map["remote"]
        assert coordinator.next_mode_at == datetime(2026, 3, 11, 10, 0, 0)

    def test_allday_event_today_followed_by_allday_event_tomorrow(self):
        """All-day Télétravail today; all-day Vacances tomorrow (keyword maps to 'home' → 'Maison').
        At 10:00 (mode=Télétravail), the first change is tomorrow midnight → Maison.
        """
        hass = make_mock_hass()
        entry = make_mock_entry()
        today_state = make_calendar_state(
            state="on",
            message="Télétravail",
            start_time="2026-03-11 00:00:00",
            end_time="2026-03-12 00:00:00",
        )
        holiday_off = make_calendar_state(state="off")
        hass.states.get.side_effect = lambda eid: today_state if eid == "calendar.teletravail" else holiday_off
        hass.services.async_call = _mock_get_events(
            "calendar.teletravail",
            [
                {"summary": "Télétravail", "start": "2026-03-11T00:00:00", "end": "2026-03-12T00:00:00"},
                {"summary": "Vacances", "start": "2026-03-12T00:00:00", "end": "2026-03-13T00:00:00"},
            ],
        )
        coordinator = HomeShiftCoordinator(hass, entry)

        now = datetime(2026, 3, 11, 10, 0, 0)  # Wednesday
        with patch("custom_components.homeshift.coordinator.dt_util") as mock_dt:
            mock_dt.now.return_value = now
            asyncio.get_event_loop().run_until_complete(coordinator.async_update_data())

        from .conftest import _fr_day_map

        # Vacances keyword maps to 'home' → 'Maison'
        assert coordinator.next_mode_predicted == _fr_day_map["home"]
        assert coordinator.next_mode_at == datetime(2026, 3, 12, 0, 0, 0)
