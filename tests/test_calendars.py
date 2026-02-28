"""Tests for the ICS calendar files.

These tests verify:
- Validity of the ICS files
- Recurring events (telework)
- Vacation periods
- French public holidays
"""

from pathlib import Path

import pytest

try:
    from icalendar import Calendar
    HAS_ICALENDAR = True
except ImportError:
    HAS_ICALENDAR = False
    Calendar = None

CALENDARS_DIR = Path(__file__).parent.parent / "calendars"
TELETRAVAIL_ICS = CALENDARS_DIR / "teletravail.ics"
JOURS_FERIES_ICS = CALENDARS_DIR / "jours_feries_fr.ics"


@pytest.mark.skipif(not HAS_ICALENDAR, reason="icalendar library not installed")
class TestCalendarsWithIcalendar:
    """Tests using the icalendar library."""

    def test_teletravail_file_exists(self):
        """Verify that the telework calendar file exists."""
        assert TELETRAVAIL_ICS.exists(), f"File {TELETRAVAIL_ICS} not found"

    def test_jours_feries_file_exists(self):
        """Verify that the public holidays calendar file exists."""
        assert JOURS_FERIES_ICS.exists(), f"File {JOURS_FERIES_ICS} not found"

    def test_teletravail_ics_valid(self):
        """Verify that the telework file is a valid ICS calendar."""
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            assert cal is not None
            assert cal.get("VERSION") == "2.0"

    def test_jours_feries_ics_valid(self):
        """Verify that the public holidays file is a valid ICS calendar."""
        with open(JOURS_FERIES_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            assert cal is not None
            assert cal.get("VERSION") == "2.0"

    def test_teletravail_has_recurring_event(self):
        """Verify there is at least one recurring 'Télétravail' event."""
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
            recurring_events = [e for e in events if "RRULE" in e]
            assert len(recurring_events) > 0, "No recurring event found"
            teletravail_recurring = [e for e in recurring_events if "Télétravail" in str(e.get("SUMMARY"))]
            assert len(teletravail_recurring) > 0, "No recurring 'Télétravail' event found"

    def test_teletravail_has_vacation_events(self):
        """Verify there are at least 2 vacation period events."""
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
            vacation_events = [e for e in events if "Vacances" in str(e.get("SUMMARY"))]
            assert len(vacation_events) >= 2, f"Expected at least 2 vacation periods, found {len(vacation_events)}"

    def test_jours_feries_has_11_holidays(self):
        """Verify there are exactly 11 French public holidays."""
        with open(JOURS_FERIES_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
            assert len(events) == 11, f"Expected 11 public holidays, found {len(events)}"

    def test_jours_feries_mandatory_holidays(self):
        """Verify the presence of the mandatory French public holidays."""
        # These are the official French holiday names stored in the ICS file
        mandatory_holidays = [
            "Nouvel An",
            "Fête du Travail",
            "Victoire 1945",
            "Fête Nationale",
            "Assomption",
            "Toussaint",
            "Armistice",
            "Noël",
        ]
        with open(JOURS_FERIES_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
            summaries = [str(e.get("SUMMARY")) for e in events]
            for holiday in mandatory_holidays:
                assert any(holiday in s for s in summaries), f"Holiday '{holiday}' not found"


class TestCalendarsBasic:
    """Basic ICS structure tests with no external dependencies."""

    def test_teletravail_file_exists(self):
        """Verify that the telework calendar file exists."""
        assert TELETRAVAIL_ICS.exists(), f"File {TELETRAVAIL_ICS} not found"

    def test_jours_feries_file_exists(self):
        """Verify that the public holidays calendar file exists."""
        assert JOURS_FERIES_ICS.exists(), f"File {JOURS_FERIES_ICS} not found"

    def test_teletravail_ics_structure(self):
        """Verify the basic structure of the telework ICS file."""
        content = TELETRAVAIL_ICS.read_text()
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VEVENT" in content
        assert "SUMMARY:Télétravail" in content
        assert "RRULE:" in content  # Recurring event must be present
        assert "SUMMARY:Vacances" in content

    def test_jours_feries_ics_structure(self):
        """Verify the basic structure of the public holidays ICS file."""
        content = JOURS_FERIES_ICS.read_text()
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VEVENT" in content
        assert "SUMMARY:Nouvel An" in content
        assert "SUMMARY:Fête du Travail" in content
        assert "SUMMARY:Fête Nationale" in content
        assert "SUMMARY:Noël" in content

    def test_jours_feries_event_count(self):
        """Verify there are approximately 11 events in the public holidays calendar."""
        content = JOURS_FERIES_ICS.read_text()
        event_count = content.count("BEGIN:VEVENT")
        assert 10 <= event_count <= 12, f"Expected ~11 events, found {event_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
