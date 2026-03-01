"""Constants for the HomeShift integration."""

DOMAIN = "homeshift"

# Configuration keys
CONF_CALENDAR_ENTITY = "calendar_entity"
CONF_HOLIDAY_CALENDAR = "holiday_calendar"
CONF_DAY_MODE_MAP = "day_mode_map"  # Mapping: internal key → display name (like thermostat)
CONF_THERMOSTAT_MODE_MAP = "thermostat_mode_map"  # Mapping: internal key → display/scheduler tag
CONF_SCHEDULERS_PER_MODE = "schedulers_per_mode"  # Scheduler entities per day mode
CONF_SCAN_INTERVAL = "scan_interval"
CONF_OVERRIDE_DURATION = "override_duration"  # minutes to lock auto-update after manual change

# Mode mapping configuration
CONF_MODE_DEFAULT = "mode_default"  # Day mode key for regular work days
CONF_MODE_WEEKEND = "mode_weekend"  # Day mode key for weekends
CONF_MODE_HOLIDAY = "mode_holiday"  # Day mode key for holidays
CONF_EVENT_MODE_MAP = "event_mode_map"  # Mapping: calendar event keyword → day mode key
CONF_MODE_ABSENCE = "mode_absence"  # Day mode key that blocks automatic updates

# Default values (keys are stable English identifiers)
DEFAULT_DAY_MODE_MAP = "Home:Home, Work:Work, Remote:Remote, Absence:Absence"
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

# Sentinel value used as today_type when no calendar event is active
EVENT_NONE = "None"

# Event period types
EVENT_PERIOD_ALL_DAY = "all_day"
EVENT_PERIOD_MORNING = "morning"
EVENT_PERIOD_AFTERNOON = "afternoon"

# Service names
SERVICE_REFRESH_SCHEDULERS = "refresh_schedulers"
SERVICE_SYNC_CALENDAR = "sync_calendar"

# Attributes
ATTR_DAY_MODE = "day_mode"
ATTR_THERMOSTAT_MODE = "thermostat_mode"


# ---------------------------------------------------------------------------
# Localized defaults (keyed by ISO 639-1 language code)
# ---------------------------------------------------------------------------
# CONF_DAY_MODE_MAP format: "Key:Display, ..."  — keys are stable English ids,
# display names are the locale-specific labels shown in the UI / select entity.
# CONF_MODE_DEFAULT / WEEKEND / HOLIDAY / ABSENCE reference the **keys** above.
# CONF_EVENT_MODE_MAP format: "EventKeyword:DayModeKey, ..." — both sides use
# the keywords / keys defined above (locale-independent).

LOCALIZED_DEFAULTS: dict[str, dict] = {
    "en": {
        CONF_DAY_MODE_MAP: "Home:Home, Work:Work, Remote:Remote, Absence:Absence",
        CONF_MODE_DEFAULT: "Work",
        CONF_MODE_WEEKEND: "Home",
        CONF_MODE_HOLIDAY: "Home",
        CONF_MODE_ABSENCE: "Absence",
        CONF_EVENT_MODE_MAP: "Vacation:Home, Remote:Remote",
        CONF_THERMOSTAT_MODE_MAP: "Off:Off, Heating:Heating, Cooling:Cooling, Ventilation:Ventilation",
    },
    "fr": {
        CONF_DAY_MODE_MAP: "Home:Maison, Work:Travail, Remote:T\u00e9l\u00e9travail, Absence:Absence",
        CONF_MODE_DEFAULT: "Work",
        CONF_MODE_WEEKEND: "Home",
        CONF_MODE_HOLIDAY: "Home",
        CONF_MODE_ABSENCE: "Absence",
        CONF_EVENT_MODE_MAP: "Vacances:Home, T\u00e9l\u00e9travail:Remote",
        CONF_THERMOSTAT_MODE_MAP: "Off:Eteint, Heating:Chauffage, Cooling:Climatisation, Ventilation:Ventilation",
    },
}


def get_localized_defaults(hass) -> dict:
    """Return defaults localized to the HA instance language."""
    lang = getattr(hass.config, "language", "en") or "en"
    lang_code = lang.split("-")[0].lower()
    return LOCALIZED_DEFAULTS.get(lang_code, LOCALIZED_DEFAULTS["en"])
