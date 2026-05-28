"""Constants for the HomeShift integration."""

DOMAIN = "homeshift"

# Configuration keys
CONF_CALENDAR_ENTITY = "calendar_entity"
CONF_HOLIDAY_CALENDAR = "holiday_calendar"
CONF_DAY_MODE_MAP = "day_mode_map"  # Mapping: internal key → display name (like thermostat)
CONF_THERMOSTAT_MODE_MAP = "thermostat_mode_map"  # Mapping: internal key → display/scheduler tag
CONF_SCHEDULERS_PER_MODE = "schedulers_per_mode"  # Scheduler entities per day mode
CONF_OVERRIDE_DURATION = "override_duration"  # minutes to lock auto-update after manual change
CONF_EARLY_SWITCH_MINUTES = "early_switch_minutes"  # minutes to pre-activate a timed event

# Mode mapping configuration
CONF_MODE_DEFAULT = "mode_default"  # Day mode key for regular work days
CONF_MODE_WEEKEND = "mode_weekend"  # Day mode key for weekends
CONF_MODE_HOLIDAY = "mode_holiday"  # Day mode key for holidays
CONF_EVENT_MODE_MAP = "event_mode_map"  # Mapping: calendar event keyword → day mode key
CONF_MODE_ABSENCE = "mode_absence"  # Day mode key that blocks automatic updates

# Default values (keys are stable English identifiers)
DEFAULT_DAY_MODE_MAP = "home:Home, work:Work, remote:Remote, away:Away"
DEFAULT_THERMOSTAT_MODE_MAP = "off:Off, heating:Heating, cooling:Cooling, ventilation:Ventilation"
# Internal key that means 'thermostat is off' — schedulers with any thermostat
# tag are disabled when the thermostat mode matches this key.
THERMOSTAT_OFF_KEY = "off"
SCAN_INTERVAL_MINUTES = 5  # hardcoded periodic refresh interval
DEFAULT_OVERRIDE_DURATION = 0  # 0 = disabled
DEFAULT_EARLY_SWITCH_MINUTES = 0  # 0 = disabled
DEFAULT_MODE_DEFAULT = "work"
DEFAULT_MODE_WEEKEND = "home"
DEFAULT_MODE_HOLIDAY = "home"
DEFAULT_EVENT_MODE_MAP = "Vacation:home, Remote:remote"
DEFAULT_MODE_ABSENCE = "away"

# Cover heat control
CONF_COVER_ENTITIES = "cover_entities"
CONF_COVER_TEMP_SENSOR = "cover_temp_sensor"
CONF_COVER_TEMP_THRESHOLD = "cover_temp_threshold"
CONF_COVER_TIME_START = "cover_time_start"
CONF_COVER_TIME_END = "cover_time_end"
CONF_COVER_ACTION = "cover_action"
CONF_COVER_MY_BUTTON = "cover_my_button"

DEFAULT_COVER_TEMP_THRESHOLD = 30.0
DEFAULT_COVER_TIME_START = "08:35:00"
DEFAULT_COVER_TIME_END = "18:00:00"
DEFAULT_COVER_ACTION = "close_cover"

# Sunrise-based scheduler adjustment
CONF_SUNRISE_SCHEDULERS = "sunrise_schedulers"
CONF_SUNRISE_EARLIEST = "sunrise_earliest"

DEFAULT_SUNRISE_EARLIEST = "07:00:00"

# Entity IDs
SELECT_DAY_MODE = "day_mode"
SELECT_THERMOSTAT_MODE = "thermostat_mode"
NUMBER_OVERRIDE_DURATION = "override_duration"
NUMBER_EARLY_SWITCH = "early_switch"
SENSOR_NEXT_SCAN = "next_scan"
SENSOR_NEXT_MODE = "next_mode"
SENSOR_NEXT_MODE_AT = "next_mode_at"
SENSOR_COVER_OPEN_TIME = "cover_open_time"
BINARY_SENSOR_COVER_HEAT_ACTIVE = "cover_heat_active"

# Sentinel value used as today_type when no calendar event is active
EVENT_NONE = "None"

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
        CONF_DAY_MODE_MAP: "home:Home, work:Work, remote:Remote, away:Away",
        CONF_MODE_DEFAULT: "work",
        CONF_MODE_WEEKEND: "home",
        CONF_MODE_HOLIDAY: "home",
        CONF_MODE_ABSENCE: "away",
        CONF_EVENT_MODE_MAP: "Vacation:home, Remote:remote",
        CONF_THERMOSTAT_MODE_MAP: "off:Off, heating:Heating, cooling:Cooling, ventilation:Ventilation",
    },
    "fr": {
        CONF_DAY_MODE_MAP: "home:Maison, work:Travail, remote:Télétravail, away:Absence",
        CONF_MODE_DEFAULT: "work",
        CONF_MODE_WEEKEND: "home",
        CONF_MODE_HOLIDAY: "home",
        CONF_MODE_ABSENCE: "away",
        CONF_EVENT_MODE_MAP: "Vacances:home, Télétravail:remote",
        CONF_THERMOSTAT_MODE_MAP: "off:Eteint, heating:Chauffage, cooling:Climatisation, ventilation:Ventilation",
    },
}


def get_localized_defaults(hass) -> dict:
    """Return defaults localized to the HA instance language."""
    lang = getattr(hass.config, "language", "en") or "en"
    lang_code = lang.split("-")[0].lower()
    return LOCALIZED_DEFAULTS.get(lang_code, LOCALIZED_DEFAULTS["en"])
