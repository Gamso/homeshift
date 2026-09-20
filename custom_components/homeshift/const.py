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

# Daily cover schedule — native open/close of the configured covers, replacing
# a pair of external Scheduler-integration entities. Kept separate from
# CONF_COVER_ENTITIES (heat protection), which targets a single cover.
# CONF_DAILY_COVER_ENTITIES is the legacy flat entity list; it was merged into
# CONF_DAILY_COVER_ITEMS (below) by the v2 -> v3 entry migration and is only
# referenced by that migration.
CONF_DAILY_COVER_ENTITIES = "daily_cover_entities"
# CONF_DAILY_COVER_OPEN_TIME_MAP format: "ModeKey:Value, ..." — Value is either
# 'sunrise' (floored at CONF_SUNRISE_EARLIEST), 'skip' (never opens
# automatically that day), or a fixed 'HH:MM' time. A mode key missing from
# the map falls back to DEFAULT_DAILY_COVER_OPEN_TIME.
CONF_DAILY_COVER_OPEN_TIME_MAP = "daily_cover_open_time_map"
# The evening close fires when the descending sun reaches
# CONF_DAILY_COVER_CLOSE_ELEVATION degrees above the horizon, as reported by
# sun.sun's 'elevation' attribute: 0 is sunset, -6 is the end of civil
# twilight (artificial light needed). A light level rather than a delay.
CONF_DAILY_COVER_CLOSE_ELEVATION = "daily_cover_close_elevation"
# Bounds offered by the config flow. Wide enough to hold every value the
# retired sunset offset could express: +-120 minutes around sunset spans
# roughly +21 to -22 degrees at 43N (measured with astral).
CLOSE_ELEVATION_MIN = -25.0
CLOSE_ELEVATION_MAX = 25.0
# Reported by the Cover Close Time sensor as 'trigger'. Not a setting: the
# elevation is the only trigger, and CLOSE_TRIGGER_SUNSET means the fallback
# had to step in because the sun never reached the configured elevation.
CLOSE_TRIGGER_ELEVATION = "elevation"
CLOSE_TRIGGER_SUNSET = "sunset"
# Retired settings, kept for the v3 -> v4 migration that converts the fixed
# sunset offset into the elevation it was landing on. Nothing else reads them.
CONF_DAILY_COVER_CLOSE_MODE = "daily_cover_close_mode"
LEGACY_CLOSE_MODE_ELEVATION = "elevation"
CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES = "daily_cover_close_offset_minutes"
# The covers driven by the daily schedule, added one at a time from the config
# flow. Stored as a list of dicts: each pairs one cover with an optional
# window/opening sensor (so the evening close can skip a cover whose window is
# still open) and an optional My position button. A cover group entity is a
# cover like any other, so a whole-house group is simply one entry.
CONF_DAILY_COVER_ITEMS = "daily_cover_items"
CONF_ITEM_COVER = "cover"
CONF_ITEM_WINDOW_SENSOR = "window_sensor"
# Optional per-cover "My" position button (Somfy RTS & co): when set, the
# evening close presses this button instead of sending close_cover, so a
# cover that must not close fully stops at its recorded favourite position.
CONF_ITEM_MY_BUTTON = "my_button"
# Window-sensor states that mean "the window is open" — a binary_sensor uses
# 'on'; 'open' covers a field pointed at a door/window entity instead.
WINDOW_OPEN_STATES = frozenset({"on", "open"})

DEFAULT_DAILY_COVER_OPEN_TIME = "08:30"
# The offset the retired setting defaulted to, used only to convert an entry
# that never touched it.
DEFAULT_DAILY_COVER_CLOSE_OFFSET_MINUTES = 10
# -2 degrees is what that default offset landed on at every season (measured
# at 48.8N: sunset + 10 min sits between -1.9 and -2.3 all year), so a fresh
# install behaves like the old one. -4 waits until the room is genuinely
# dark, -6 is the end of civil twilight.
DEFAULT_DAILY_COVER_CLOSE_ELEVATION = -2.0

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
BINARY_SENSOR_COVERS_LEFT_OPEN = "covers_left_open"

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


def parse_key_value_map(raw: str, *, lower_keys: bool = False) -> dict[str, str]:
    """Parse a 'Key:Value, Key:Value, ...' configuration string.

    Used by every mapping option of the integration: day modes, thermostat
    modes, event keywords and the per-mode cover open times. Entries with no
    colon, an empty key or an empty value are skipped; only the first colon
    separates a pair, so a value may contain one ('work:08:30').
    Pass lower_keys=True for case-insensitive lookups (event keywords).
    """
    mapping: dict[str, str] = {}
    if not raw:
        return mapping
    for pair in raw.split(","):
        key, separator, value = pair.partition(":")
        if not separator:
            continue
        key, value = key.strip(), value.strip()
        if key and value:
            mapping[key.lower() if lower_keys else key] = value
    return mapping


def get_localized_defaults(hass) -> dict:
    """Return defaults localized to the HA instance language."""
    lang = getattr(hass.config, "language", "en") or "en"
    lang_code = lang.split("-")[0].lower()
    return LOCALIZED_DEFAULTS.get(lang_code, LOCALIZED_DEFAULTS["en"])
