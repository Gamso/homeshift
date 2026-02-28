"""Tests automatiques pour les calendriers ICS.

Ces tests vérifient :
- La validité des fichiers ICS
- Les événements récurrents (télétravail le mardi)
- Les périodes de vacances
- Les jours fériés français
"""
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

# Tentative d'import de la bibliothèque icalendar
try:
    from icalendar import Calendar
    HAS_ICALENDAR = True
except ImportError:
    HAS_ICALENDAR = False
    Calendar = None

# Chemin vers les fichiers ICS
CALENDARS_DIR = Path(__file__).parent.parent / "calendars"
TELETRAVAIL_ICS = CALENDARS_DIR / "teletravail.ics"
JOURS_FERIES_ICS = CALENDARS_DIR / "jours_feries_fr.ics"


@pytest.mark.skipif(not HAS_ICALENDAR, reason="icalendar library not installed")
class TestCalendarsWithIcalendar:
    """Tests utilisant la bibliothèque icalendar."""

    def test_teletravail_file_exists(self):
        """Vérifie que le fichier calendrier télétravail existe."""
        assert TELETRAVAIL_ICS.exists(), f"Le fichier {TELETRAVAIL_ICS} n'existe pas"

    def test_jours_feries_file_exists(self):
        """Vérifie que le fichier calendrier jours fériés existe."""
        assert JOURS_FERIES_ICS.exists(), f"Le fichier {JOURS_FERIES_ICS} n'existe pas"

    def test_teletravail_ics_valid(self):
        """Vérifie que le fichier télétravail est un ICS valide."""
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            assert cal is not None
            assert cal.get("VERSION") == "2.0"

    def test_jours_feries_ics_valid(self):
        """Vérifie que le fichier jours fériés est un ICS valide."""
        with open(JOURS_FERIES_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            assert cal is not None
            assert cal.get("VERSION") == "2.0"

    def test_teletravail_has_recurring_event(self):
        """Vérifie qu'il y a un événement récurrent 'Télétravail'."""
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]

            # Cherche un événement avec RRULE (récurrent)
            recurring_events = [e for e in events if "RRULE" in e]
            assert len(recurring_events) > 0, "Aucun événement récurrent trouvé"

            # Vérifie que c'est bien 'Télétravail'
            teletravail_event = [e for e in recurring_events if "Télétravail" in str(e.get("SUMMARY"))]
            assert len(teletravail_event) > 0, "Événement récurrent 'Télétravail' non trouvé"

    def test_teletravail_has_vacation_events(self):
        """Vérifie qu'il y a au moins 2 périodes de vacances."""
        with open(TELETRAVAIL_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]

            # Cherche les événements 'Vacances'
            vacation_events = [e for e in events if "Vacances" in str(e.get("SUMMARY"))]
            assert len(vacation_events) >= 2, f"Attendu au moins 2 périodes de vacances, trouvé {len(vacation_events)}"

    def test_jours_feries_has_11_holidays(self):
        """Vérifie qu'il y a exactement 11 jours fériés français."""
        with open(JOURS_FERIES_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
            assert len(events) == 11, f"Attendu 11 jours fériés, trouvé {len(events)}"

    def test_jours_feries_mandatory_holidays(self):
        """Vérifie la présence des jours fériés obligatoires."""
        mandatory_holidays = [
            "Nouvel An",
            "Fête du Travail",
            "Victoire 1945",
            "Fête Nationale",
            "Assomption",
            "Toussaint",
            "Armistice",
            "Noël"
        ]

        with open(JOURS_FERIES_ICS, "rb") as f:
            cal = Calendar.from_ical(f.read())
            events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
            summaries = [str(e.get("SUMMARY")) for e in events]

            for holiday in mandatory_holidays:
                assert any(holiday in s for s in summaries), f"Jour férié '{holiday}' non trouvé"


class TestCalendarsBasic:
    """Tests basiques sans dépendance externe."""

    def test_teletravail_file_exists(self):
        """Vérifie que le fichier calendrier télétravail existe."""
        assert TELETRAVAIL_ICS.exists(), f"Le fichier {TELETRAVAIL_ICS} n'existe pas"

    def test_jours_feries_file_exists(self):
        """Vérifie que le fichier calendrier jours fériés existe."""
        assert JOURS_FERIES_ICS.exists(), f"Le fichier {JOURS_FERIES_ICS} n'existe pas"

    def test_teletravail_ics_structure(self):
        """Vérifie la structure basique du fichier télétravail."""
        content = TELETRAVAIL_ICS.read_text()
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VEVENT" in content
        assert "SUMMARY:Télétravail" in content
        assert "RRULE:" in content  # Événement récurrent
        assert "SUMMARY:Vacances" in content

    def test_jours_feries_ics_structure(self):
        """Vérifie la structure basique du fichier jours fériés."""
        content = JOURS_FERIES_ICS.read_text()
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "END:VEVENT" in content

        # Vérifie quelques jours fériés
        assert "SUMMARY:Nouvel An" in content
        assert "SUMMARY:Fête du Travail" in content
        assert "SUMMARY:Fête Nationale" in content
        assert "SUMMARY:Noël" in content

    def test_teletravail_has_multiple_events(self):
        """Vérifie qu'il y a plusieurs événements dans télétravail."""
        content = TELETRAVAIL_ICS.read_text()
        event_count = content.count("BEGIN:VEVENT")
        assert event_count >= 3, f"Attendu au moins 3 événements, trouvé {event_count}"

    def test_jours_feries_event_count(self):
        """Vérifie qu'il y a environ 11 événements dans jours fériés."""
        content = JOURS_FERIES_ICS.read_text()
        event_count = content.count("BEGIN:VEVENT")
        assert 10 <= event_count <= 12, f"Attendu environ 11 événements, trouvé {event_count}"

    def test_ics_files_encoding(self):
        """Vérifie que les fichiers sont en UTF-8."""
        # Test télétravail
        content = TELETRAVAIL_ICS.read_text(encoding="utf-8")
        assert "Télétravail" in content
        assert "été" in content or "Noël" in content

        # Test jours fériés
        content = JOURS_FERIES_ICS.read_text(encoding="utf-8")
        assert "français" in content or "Noël" in content

    def test_www_calendars_copied(self):
        """Vérifie que les calendriers sont copiés dans www/calendars."""
        www_dir = Path(__file__).parent.parent / "config" / "www" / "calendars"
        assert www_dir.exists(), "Le dossier www/calendars n'existe pas"

        www_teletravail = www_dir / "teletravail.ics"
        www_feries = www_dir / "jours_feries_fr.ics"

        assert www_teletravail.exists(), f"{www_teletravail} n'existe pas"
        assert www_feries.exists(), f"{www_feries} n'existe pas"


# Test de compatibilité Home Assistant (sans dépendance HA)
class TestHomeAssistantCompatibility:
    """Tests de compatibilité avec Home Assistant."""

    def test_ics_mime_type_compatible(self):
        """Vérifie que les fichiers ont l'extension .ics."""
        assert TELETRAVAIL_ICS.suffix == ".ics"
        assert JOURS_FERIES_ICS.suffix == ".ics"

    def test_ics_accessible_via_www(self):
        """Vérifie que les fichiers sont accessibles via www/."""
        www_calendars = Path(__file__).parent.parent / "config" / "www" / "calendars"

        if www_calendars.exists():
            www_files = list(www_calendars.glob("*.ics"))
            assert len(www_files) >= 2, f"Attendu au moins 2 fichiers ICS dans www/calendars, trouvé {len(www_files)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
