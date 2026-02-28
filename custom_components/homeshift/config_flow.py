"""Config flow for HomeShift integration."""
from __future__ import annotations

import logging
from typing import Any, Self

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_HOLIDAY_CALENDAR,
    CONF_DAY_MODES,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCHEDULERS_PER_MODE,
    CONF_SCAN_INTERVAL,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_DAY_MODES,
    DEFAULT_THERMOSTAT_MODE_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_MODE_ABSENCE,
    DEFAULT_EVENT_MODE_MAP,
    LOCALIZED_DEFAULTS,
    get_localized_defaults,
)

_LOGGER = logging.getLogger(__name__)

# Aliases for backwards compatibility
_LOCALIZED_DEFAULTS = LOCALIZED_DEFAULTS
_get_localized_defaults = get_localized_defaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _calendars_schema(data: dict[str, Any]) -> vol.Schema:
    """Build the calendars & schedule form schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_CALENDAR_ENTITY,
                default=data.get(CONF_CALENDAR_ENTITY, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar"),
            ),
            vol.Required(
                CONF_HOLIDAY_CALENDAR,
                default=data.get(CONF_HOLIDAY_CALENDAR, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar"),
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=1440,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        }
    )


def _parse_thermostat_map(map_str: str) -> dict[str, str]:
    """Parse 'Key:Display, ...' string into an ordered dict."""
    result: dict[str, str] = {}
    for pair in map_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, _, display = pair.partition(":")
            result[key.strip()] = display.strip()
    return result


def _thermostat_display_fields(data: dict[str, Any]) -> dict:
    """Return one TextSelector field per thermostat key (key = label)."""
    current_map = _parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))
    fields: dict = {}
    for key, display in current_map.items():
        field_name = f"thermostat_display_{key.lower()}"
        fields[
            vol.Optional(
                field_name,
                default=display,
            )
        ] = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))
    return fields


def _rebuild_thermostat_map(user_input: dict[str, Any], data: dict[str, Any]) -> str:
    """Reconstruct CONF_THERMOSTAT_MODE_MAP from individual display fields."""
    current_map = _parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))
    pairs: list[str] = []
    for key, default_display in current_map.items():
        field_name = f"thermostat_display_{key.lower()}"
        display = user_input.pop(field_name, default_display)
        pairs.append(f"{key}:{display}")
    return ", ".join(pairs)


def _mapping_schema(data: dict[str, Any]) -> vol.Schema:
    """Build the mode-mapping form schema with collapsible sections."""
    text = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))

    # Section 1: day modes + default modes
    day_modes_schema = vol.Schema(
        {
            vol.Optional(
                CONF_DAY_MODES,
                default=data.get(CONF_DAY_MODES, ", ".join(DEFAULT_DAY_MODES)),
            ): str,
            vol.Optional(
                CONF_MODE_DEFAULT,
                default=data.get(CONF_MODE_DEFAULT, DEFAULT_MODE_DEFAULT),
            ): text,
            vol.Optional(
                CONF_MODE_ABSENCE,
                default=data.get(CONF_MODE_ABSENCE, DEFAULT_MODE_ABSENCE),
            ): text,
            vol.Optional(
                CONF_MODE_WEEKEND,
                default=data.get(CONF_MODE_WEEKEND, DEFAULT_MODE_WEEKEND),
            ): text,
            vol.Optional(
                CONF_MODE_HOLIDAY,
                default=data.get(CONF_MODE_HOLIDAY, DEFAULT_MODE_HOLIDAY),
            ): text,
        }
    )

    # Section 2: event map + thermostat display names
    thermostat_fields_dict: dict = {
        vol.Optional(
            CONF_EVENT_MODE_MAP,
            default=data.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP),
        ): str,
    }
    thermostat_fields_dict.update(_thermostat_display_fields(data))
    thermostat_schema = vol.Schema(thermostat_fields_dict)

    return vol.Schema(
        {
            vol.Required("day_modes_section"): section(day_modes_schema, {"collapsed": False}),
            vol.Required("thermostat_section"): section(thermostat_schema, {"collapsed": False}),
        }
    )


def _validate_calendars(hass, user_input: dict[str, Any]) -> dict[str, str]:
    """Return form errors for bad calendar entities."""
    errors: dict[str, str] = {}
    cal = user_input.get(CONF_CALENDAR_ENTITY)
    if cal and not hass.states.get(cal):
        errors[CONF_CALENDAR_ENTITY] = "invalid_calendar"
    hol = user_input.get(CONF_HOLIDAY_CALENDAR)
    if hol and not hass.states.get(hol):
        errors[CONF_HOLIDAY_CALENDAR] = "invalid_calendar"
    return errors


def _parse_day_modes(data: dict[str, Any]) -> list[str]:
    """Return the list of configured day modes."""
    raw = data.get(CONF_DAY_MODES, ", ".join(DEFAULT_DAY_MODES))
    return [m.strip() for m in raw.split(",") if m.strip()]


def _get_scheduler_options(hass) -> list[selector.SelectOptionDict]:
    """Return SelectSelector options for scheduler-like switch entities."""
    options: list[selector.SelectOptionDict] = []
    for state in hass.states.async_all("switch"):
        if "schedule" in state.entity_id.lower() or state.attributes.get("next_trigger") is not None:
            friendly = state.attributes.get("friendly_name", state.entity_id)
            options.append(
                {
                    "value": state.entity_id,
                    "label": f"{friendly} ({state.entity_id})",
                }
            )
    options.sort(key=lambda x: x["label"])
    return options


def _scheduler_selector(hass) -> selector.SelectSelector | selector.EntitySelector:
    """Return the best selector for scheduler entities."""
    opts = _get_scheduler_options(hass)
    if opts:
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=opts,
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="switch", multiple=True))


def _schedulers_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build scheduler form schema – one multi-select per day mode."""
    day_modes = _parse_day_modes(data)
    current_schedulers: dict[str, list] = data.get(CONF_SCHEDULERS_PER_MODE, {})
    sel = _scheduler_selector(hass)
    schema_dict: dict = {}
    for mode in day_modes:
        current_value = current_schedulers.get(mode, [])
        schema_dict[vol.Optional(mode, default=current_value)] = sel
    return vol.Schema(schema_dict)


def _extract_schedulers(user_input: dict[str, Any], data: dict[str, Any]) -> dict[str, list]:
    """Extract scheduler assignments from form user_input."""
    day_modes = _parse_day_modes(data)
    result: dict[str, list] = {}
    for mode in day_modes:
        value = user_input.get(mode, [])
        if isinstance(value, str):
            value = [value] if value else []
        result[mode] = value
    return result


# ---------------------------------------------------------------------------
# Config flow (initial setup) – menu-based
# ---------------------------------------------------------------------------


class HomeShiftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeShift."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._data: dict[str, Any] = {}

    def is_matching(self, other_flow: Self) -> bool:
        """Return True if another in-progress flow matches this one (not used)."""
        return False

    # -- helpers -----------------------------------------------------------

    def _effective_data(self) -> dict[str, Any]:
        """Return _data merged over localized defaults (for schema builders)."""
        return {**_get_localized_defaults(self.hass), **self._data}

    def _is_config_complete(self) -> bool:
        """Return True when the minimum required configuration is present."""
        return bool(self._data.get(CONF_CALENDAR_ENTITY))

    # -- entry point -------------------------------------------------------

    async def async_step_user(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Entry point – redirect to the menu."""
        return await self.async_step_menu()

    # -- menu --------------------------------------------------------------

    async def async_step_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the configuration menu."""
        menu_options = ["calendars", "mapping", "schedulers"]
        if self._is_config_complete():
            menu_options.append("finalize")
        return self.async_show_menu(step_id="menu", menu_options=menu_options)

    # -- calendars ---------------------------------------------------------

    async def async_step_calendars(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure calendar entities and scan interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_calendars(self.hass, user_input)
            if not errors:
                self._data.update(user_input)
                return await self.async_step_menu()

        return self.async_show_form(
            step_id="calendars",
            data_schema=_calendars_schema(self._effective_data()),
            errors=errors,
        )

    # -- mapping -----------------------------------------------------------

    async def async_step_mapping(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure day-mode & thermostat-mode mapping."""
        if user_input is not None:
            # Flatten section-nested input from the two sections
            flat: dict[str, Any] = {
                **user_input.get("day_modes_section", {}),
                **user_input.get("thermostat_section", {}),
            }
            flat[CONF_THERMOSTAT_MODE_MAP] = _rebuild_thermostat_map(flat, self._data)
            self._data.update(flat)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="mapping",
            data_schema=_mapping_schema(self._effective_data()),
        )

    # -- schedulers --------------------------------------------------------

    async def async_step_schedulers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Assign scheduler entities to each day mode."""
        if user_input is not None:
            self._data[CONF_SCHEDULERS_PER_MODE] = _extract_schedulers(user_input, self._data)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="schedulers",
            data_schema=_schedulers_schema(self.hass, self._data),
        )

    # -- finalize ----------------------------------------------------------

    async def async_step_finalize(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(title="HomeShift", data=self._data)

    # -- options flow accessor ---------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HomeShiftOptionsFlow:
        """Get the options flow for this handler."""
        return HomeShiftOptionsFlow()


# ---------------------------------------------------------------------------
# Options flow – menu-based
# ---------------------------------------------------------------------------


class HomeShiftOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HomeShift."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._data: dict[str, Any] = {}

    # -- helpers -----------------------------------------------------------

    def _is_config_complete(self) -> bool:
        """Return True when the minimum required configuration is present."""
        return bool(self._data.get(CONF_CALENDAR_ENTITY))

    def _effective_data(self) -> dict[str, Any]:
        """Return _data merged over localized defaults (for schema builders)."""
        return {**_get_localized_defaults(self.hass), **self._data}

    # -- entry point -------------------------------------------------------

    async def async_step_init(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Entry point – pre-populate from existing entry, then show menu."""
        self._data = dict(self.config_entry.data)
        return await self.async_step_menu()

    # -- menu --------------------------------------------------------------

    async def async_step_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the options menu."""
        menu_options = ["calendars", "mapping", "schedulers"]
        if self._is_config_complete():
            menu_options.append("finalize")
        return self.async_show_menu(step_id="menu", menu_options=menu_options)

    # -- calendars ---------------------------------------------------------

    async def async_step_calendars(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure calendar entities and scan interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_calendars(self.hass, user_input)
            if not errors:
                self._data.update(user_input)
                return await self.async_step_menu()

        return self.async_show_form(
            step_id="calendars",
            data_schema=_calendars_schema(self._effective_data()),
            errors=errors,
        )

    # -- mapping -----------------------------------------------------------

    async def async_step_mapping(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure day-mode & thermostat-mode mapping."""
        if user_input is not None:
            # Flatten section-nested input from the two sections
            flat: dict[str, Any] = {
                **user_input.get("day_modes_section", {}),
                **user_input.get("thermostat_section", {}),
            }
            flat[CONF_THERMOSTAT_MODE_MAP] = _rebuild_thermostat_map(flat, self._data)
            self._data.update(flat)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="mapping",
            data_schema=_mapping_schema(self._effective_data()),
        )

    # -- schedulers --------------------------------------------------------

    async def async_step_schedulers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Assign scheduler entities to each day mode."""
        if user_input is not None:
            self._data[CONF_SCHEDULERS_PER_MODE] = _extract_schedulers(user_input, self._data)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="schedulers",
            data_schema=_schedulers_schema(self.hass, self._data),
        )

    # -- finalize ----------------------------------------------------------

    async def async_step_finalize(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Save options."""
        return self.async_create_entry(title="", data=self._data)
