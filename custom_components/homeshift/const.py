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

# Default values
DEFAULT_DAY_MODES = ["Maison", "Travail", "Télétravail", "Absence"]
DEFAULT_THERMOSTAT_MODE_MAP = "Off:Eteint, Heating:Chauffage, Cooling:Climatisation, Ventilation:Ventilation"
# Internal key that means 'thermostat is off' — schedulers with any thermostat
# tag are disabled when the thermostat mode matches this key.
THERMOSTAT_OFF_KEY = "Off"
DEFAULT_SCAN_INTERVAL = 60  # minutes
DEFAULT_OVERRIDE_DURATION = 0  # 0 = disabled
DEFAULT_MODE_DEFAULT = "Travail"
DEFAULT_MODE_WEEKEND = "Maison"
DEFAULT_MODE_HOLIDAY = "Maison"
DEFAULT_EVENT_MODE_MAP = "Vacances:Maison, Télétravail:Télétravail"
DEFAULT_MODE_ABSENCE = "Absence"

# Entity IDs
SELECT_DAY_MODE = "day_mode"
SELECT_THERMOSTAT_MODE = "thermostat_mode"
SENSOR_NEXT_DAY_TYPE = "next_day_type"
NUMBER_OVERRIDE_DURATION = "override_duration"

# Calendar events
EVENT_NONE = "Aucun"
EVENT_VACATION = "Vacances"
EVENT_TELEWORK = "Télétravail"

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
