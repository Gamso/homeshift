"""Constants for the HomeShift integration."""

DOMAIN = "homeshift"

# Configuration keys
CONF_CALENDAR_ENTITY = "calendar_entity"
CONF_HOLIDAY_CALENDAR = "holiday_calendar"
CONF_DAY_MODES = "day_modes"
CONF_THERMOSTAT_MODE_MAP = "thermostat_mode_map"  # Mapping: internal key → display/scheduler tag
CONF_SCHEDULERS_PER_MODE = "schedulers_per_mode"  # Scheduler entities per day mode
CONF_SCAN_INTERVAL = "scan_interval"
CONF_OVERRIDE_DURATION = "override_duration"  # minutes to lock auto-update after manual change

# Mode mapping configuration
CONF_MODE_DEFAULT = "mode_default"  # Mode for regular work days
CONF_MODE_WEEKEND = "mode_weekend"  # Mode for weekends
CONF_MODE_HOLIDAY = "mode_holiday"  # Mode for holidays/vacances
CONF_EVENT_MODE_MAP = "event_mode_map"  # Mapping: calendar event → day mode
CONF_MODE_ABSENCE = "mode_absence"  # Mode that blocks automatic updates

# Default values (English baseline — localized defaults are provided by config_flow)
DEFAULT_DAY_MODES = ["Home", "Work", "Remote", "Absence"]
DEFAULT_THERMOSTAT_MODE_MAP = "Off:Off, Heating:Heating, Cooling:Cooling, Ventilation:Ventilation"
# Internal key that means 'thermostat is off' — schedulers with any thermostat
# tag are disabled when the thermostat mode matches this key.
THERMOSTAT_OFF_KEY = "Off"
DEFAULT_SCAN_INTERVAL = 60  # minutes
DEFAULT_OVERRIDE_DURATION = 0  # 0 = disabled
DEFAULT_MODE_DEFAULT = "Work"
DEFAULT_MODE_WEEKEND = "Home"
DEFAULT_MODE_HOLIDAY = "Home"
DEFAULT_EVENT_MODE_MAP = "Vacation:Home, Remote:Remote"
DEFAULT_MODE_ABSENCE = "Absence"

# Entity IDs
SELECT_DAY_MODE = "day_mode"
SELECT_THERMOSTAT_MODE = "thermostat_mode"
NUMBER_OVERRIDE_DURATION = "override_duration"

# Calendar events (English baseline — localized values are in LOCALIZED_DEFAULTS)
EVENT_NONE = "None"
EVENT_VACATION = "Vacation"
EVENT_REMOTE = "Remote"

# Keys for localized event strings inside LOCALIZED_DEFAULTS
KEY_EVENT_NONE = "event_none"
KEY_EVENT_VACATION = "event_vacation"
KEY_EVENT_REMOTE = "event_remote"

# Event period types
EVENT_PERIOD_ALL_DAY = "all_day"
EVENT_PERIOD_MORNING = "morning"
EVENT_PERIOD_AFTERNOON = "afternoon"

# Service names
SERVICE_REFRESH_SCHEDULERS = "refresh_schedulers"
SERVICE_CHECK_NEXT_DAY = "check_next_day"

# Attributes
ATTR_DAY_MODE = "day_mode"
ATTR_THERMOSTAT_MODE = "thermostat_mode"


# ---------------------------------------------------------------------------
# Localized defaults (keyed by ISO 639-1 language code)
# ---------------------------------------------------------------------------

LOCALIZED_DEFAULTS: dict[str, dict] = {
    "en": {
        CONF_DAY_MODES: "Home, Work, Remote, Absence",
        CONF_MODE_DEFAULT: "Work",
        CONF_MODE_WEEKEND: "Home",
        CONF_MODE_HOLIDAY: "Home",
        CONF_MODE_ABSENCE: "Absence",
        CONF_EVENT_MODE_MAP: "Vacation:Home, Remote:Remote",
        CONF_THERMOSTAT_MODE_MAP: "Off:Off, Heating:Heating, Cooling:Cooling, Ventilation:Ventilation",
        KEY_EVENT_NONE: "None",
        KEY_EVENT_VACATION: "Vacation",
        KEY_EVENT_REMOTE: "Remote",
    },
    "fr": {
        CONF_DAY_MODES: "Maison, Travail, T\u00e9l\u00e9travail, Absence",
        CONF_MODE_DEFAULT: "Travail",
        CONF_MODE_WEEKEND: "Maison",
        CONF_MODE_HOLIDAY: "Maison",
        CONF_MODE_ABSENCE: "Absence",
        CONF_EVENT_MODE_MAP: "Vacances:Maison, T\u00e9l\u00e9travail:T\u00e9l\u00e9travail",
        CONF_THERMOSTAT_MODE_MAP: "Off:Eteint, Heating:Chauffage, Cooling:Climatisation, Ventilation:Ventilation",
        KEY_EVENT_NONE: "Aucun",
        KEY_EVENT_VACATION: "Vacances",
        KEY_EVENT_REMOTE: "T\u00e9l\u00e9travail",
    },
}


def get_localized_defaults(hass) -> dict:
    """Return defaults localized to the HA instance language."""
    lang = getattr(hass.config, "language", "en") or "en"
    lang_code = lang.split("-")[0].lower()
    return LOCALIZED_DEFAULTS.get(lang_code, LOCALIZED_DEFAULTS["en"])
