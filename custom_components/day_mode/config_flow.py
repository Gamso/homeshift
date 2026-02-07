"""Config flow for Day Mode integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODES,
    CONF_THERMOSTAT_MODES,
    CONF_CHECK_TIME,
    DEFAULT_DAY_MODES,
    DEFAULT_THERMOSTAT_MODES,
    DEFAULT_CHECK_TIME,
)

_LOGGER = logging.getLogger(__name__)


class DayModeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Day Mode."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the calendar entity exists
            calendar_entity = user_input.get(CONF_CALENDAR_ENTITY)
            if calendar_entity and not self.hass.states.get(calendar_entity):
                errors[CONF_CALENDAR_ENTITY] = "invalid_calendar"
            
            holiday_calendar = user_input.get(CONF_HOLIDAY_CALENDAR)
            if holiday_calendar and not self.hass.states.get(holiday_calendar):
                errors[CONF_HOLIDAY_CALENDAR] = "invalid_calendar"
            
            if not errors:
                return self.async_create_entry(
                    title="Day Mode",
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CALENDAR_ENTITY,
                    default=""
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Optional(
                    CONF_HOLIDAY_CALENDAR,
                    default=""
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Optional(
                    CONF_DAY_MODES,
                    default=", ".join(DEFAULT_DAY_MODES)
                ): str,
                vol.Optional(
                    CONF_THERMOSTAT_MODES,
                    default=", ".join(DEFAULT_THERMOSTAT_MODES)
                ): str,
                vol.Optional(
                    CONF_CHECK_TIME,
                    default=DEFAULT_CHECK_TIME
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DayModeOptionsFlow:
        """Get the options flow for this handler."""
        return DayModeOptionsFlow(config_entry)


class DayModeOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Day Mode."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the calendar entity exists
            calendar_entity = user_input.get(CONF_CALENDAR_ENTITY)
            if calendar_entity and not self.hass.states.get(calendar_entity):
                errors[CONF_CALENDAR_ENTITY] = "invalid_calendar"
            
            holiday_calendar = user_input.get(CONF_HOLIDAY_CALENDAR)
            if holiday_calendar and not self.hass.states.get(holiday_calendar):
                errors[CONF_HOLIDAY_CALENDAR] = "invalid_calendar"
            
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current_calendar = self.config_entry.data.get(CONF_CALENDAR_ENTITY, "")
        current_holiday = self.config_entry.data.get(CONF_HOLIDAY_CALENDAR, "")
        current_day_modes = self.config_entry.data.get(
            CONF_DAY_MODES, ", ".join(DEFAULT_DAY_MODES)
        )
        current_thermostat_modes = self.config_entry.data.get(
            CONF_THERMOSTAT_MODES, ", ".join(DEFAULT_THERMOSTAT_MODES)
        )
        current_check_time = self.config_entry.data.get(
            CONF_CHECK_TIME, DEFAULT_CHECK_TIME
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CALENDAR_ENTITY,
                    default=current_calendar
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Optional(
                    CONF_HOLIDAY_CALENDAR,
                    default=current_holiday
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Optional(
                    CONF_DAY_MODES,
                    default=current_day_modes
                ): str,
                vol.Optional(
                    CONF_THERMOSTAT_MODES,
                    default=current_thermostat_modes
                ): str,
                vol.Optional(
                    CONF_CHECK_TIME,
                    default=current_check_time
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )
