"""Constants for the Day Mode integration."""

DOMAIN = "day_mode"

# Configuration keys
CONF_CALENDAR_ENTITY = "calendar_entity"
CONF_HOLIDAY_CALENDAR = "holiday_calendar"
CONF_DAY_MODES = "day_modes"
CONF_THERMOSTAT_MODES = "thermostat_modes"
CONF_CHECK_TIME = "check_time"

# Default values
DEFAULT_DAY_MODES = ["Maison", "Travail", "Télétravail", "Absence"]
DEFAULT_THERMOSTAT_MODES = ["Eteint", "Chauffage", "Climatisation", "Ventilation"]
DEFAULT_CHECK_TIME = "00:10:00"

# Entity IDs
SELECT_MODE_JOUR = "mode_jour"
SELECT_MODE_THERMOSTAT = "mode_thermostat"
SENSOR_NEXT_DAY_TYPE = "next_day_type"

# Calendar events
EVENT_VACANCES = "Vacances"
EVENT_TELETRAVAIL = "Télétravail"

# Service names
SERVICE_REFRESH_SCHEDULERS = "refresh_schedulers"
SERVICE_CHECK_NEXT_DAY = "check_next_day"

# Attributes
ATTR_DAY_MODE = "day_mode"
ATTR_THERMOSTAT_MODE = "thermostat_mode"
