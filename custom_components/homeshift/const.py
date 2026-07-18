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

# Cover heat control — the active window is no longer independently
# configured: it's fully derived from the Daily Cover Schedule feature
# (below), i.e. between cover_open_time and daily_close_time. Heat protection
# is therefore inert until Daily Cover Schedule is configured.
CONF_COVER_ENTITIES = "cover_entities"
CONF_COVER_TEMP_SENSOR = "cover_temp_sensor"
CONF_COVER_TEMP_THRESHOLD = "cover_temp_threshold"
CONF_COVER_ACTION = "cover_action"
CONF_COVER_MY_BUTTON = "cover_my_button"

DEFAULT_COVER_TEMP_THRESHOLD = 30.0
DEFAULT_COVER_ACTION = "close_cover"

# Proactive (forecast-based) closing — closes ahead of the reactive threshold
# so covers shade the room before, not after, the heat has already built up.
CONF_COVER_WEATHER_ENTITY = "cover_weather_entity"
CONF_COVER_FORECAST_THRESHOLD = "cover_forecast_threshold"

DEFAULT_COVER_FORECAST_THRESHOLD = 28.0

# Earliest sunrise-based opening time — used by the Daily Cover Schedule's
# 'sunrise' open-time value (floors sunrise so covers never open too early).
CONF_SUNRISE_EARLIEST = "sunrise_earliest"

DEFAULT_SUNRISE_EARLIEST = "07:00:00"

# Daily cover schedule — native open/close of a cover group (e.g. a whole-house
# volet group), replacing a pair of external Scheduler-integration entities.
# Kept separate from CONF_COVER_ENTITIES (heat protection), which targets a
# single cover — the daily schedule is meant for a group entity instead.
CONF_DAILY_COVER_ENTITIES = "daily_cover_entities"
# CONF_DAILY_COVER_OPEN_TIME_MAP format: "ModeKey:Value, ..." — Value is either
# 'sunrise' (floored at CONF_SUNRISE_EARLIEST), 'skip' (never opens
# automatically that day), or a fixed 'HH:MM' time. A mode key missing from
# the map falls back to DEFAULT_DAILY_COVER_OPEN_TIME.
CONF_DAILY_COVER_OPEN_TIME_MAP = "daily_cover_open_time_map"
CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES = "daily_cover_close_offset_minutes"

DEFAULT_DAILY_COVER_OPEN_TIME = "08:30"
DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES = 10

# Entity IDs
SELECT_DAY_MODE = "day_mode"
SELECT_THERMOSTAT_MODE = "thermostat_mode"
NUMBER_OVERRIDE_DURATION = "override_duration"
NUMBER_EARLY_SWITCH = "early_switch"
SENSOR_NEXT_SCAN = "next_scan"
SENSOR_NEXT_MODE = "next_mode"
SENSOR_NEXT_MODE_AT = "next_mode_at"
SENSOR_COVER_OPEN_TIME = "cover_open_time"
SENSOR_COVER_CLOSE_TIME = "cover_close_time"
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
