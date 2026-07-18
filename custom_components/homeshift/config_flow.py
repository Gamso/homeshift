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
    CONF_DAY_MODE_MAP,
    CONF_THERMOSTAT_MODE_MAP,
    CONF_SCHEDULERS_PER_MODE,
    CONF_MODE_DEFAULT,
    CONF_MODE_WEEKEND,
    CONF_MODE_HOLIDAY,
    CONF_EVENT_MODE_MAP,
    CONF_MODE_ABSENCE,
    DEFAULT_DAY_MODE_MAP,
    DEFAULT_THERMOSTAT_MODE_MAP,
    DEFAULT_MODE_DEFAULT,
    DEFAULT_MODE_WEEKEND,
    DEFAULT_MODE_HOLIDAY,
    DEFAULT_MODE_ABSENCE,
    DEFAULT_EVENT_MODE_MAP,
    CONF_COVER_ENTITIES,
    CONF_COVER_TEMP_SENSOR,
    CONF_COVER_TEMP_THRESHOLD,
    CONF_COVER_TIME_START,
    CONF_COVER_TIME_END,
    CONF_COVER_ACTION,
    CONF_COVER_MY_BUTTON,
    DEFAULT_COVER_TEMP_THRESHOLD,
    DEFAULT_COVER_TIME_START,
    DEFAULT_COVER_TIME_END,
    DEFAULT_COVER_ACTION,
    CONF_COVER_WEATHER_ENTITY,
    CONF_COVER_FORECAST_THRESHOLD,
    DEFAULT_COVER_FORECAST_THRESHOLD,
    CONF_COVER_EVENING_REOPEN_TEMP,
    DEFAULT_COVER_EVENING_REOPEN_TEMP,
    CONF_SUNRISE_SCHEDULERS,
    CONF_SUNRISE_EARLIEST,
    DEFAULT_SUNRISE_EARLIEST,
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
        }
    )


def _parse_day_mode_map(map_str: str) -> dict[str, str]:
    """Parse 'Key:Display, ...' string into an ordered dict."""
    result: dict[str, str] = {}
    for pair in map_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, _, display = pair.partition(":")
            result[key.strip()] = display.strip()
    return result


def _day_mode_display_fields(data: dict[str, Any]) -> dict:
    """Return one TextSelector field per day mode key (key = label)."""
    current_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    fields: dict = {}
    for key, display in current_map.items():
        field_name = f"day_display_{key.lower()}"
        fields[
            vol.Optional(
                field_name,
                default=display,
            )
        ] = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))
    return fields


def _rebuild_day_mode_map(user_input: dict[str, Any], data: dict[str, Any]) -> str:
    """Reconstruct CONF_DAY_MODE_MAP from individual display fields."""
    current_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    pairs: list[str] = []
    for key, default_display in current_map.items():
        field_name = f"day_display_{key.lower()}"
        display = user_input.pop(field_name, default_display)
        pairs.append(f"{key}:{display}")
    return ", ".join(pairs)


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

    # Section 1: day mode display names (one field per key, like thermostat)
    day_fields_dict: dict = {}
    day_fields_dict.update(_day_mode_display_fields(data))
    day_modes_schema = vol.Schema(day_fields_dict)

    # Section 2: default mode assignments
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    mode_keys = list(day_mode_map.keys())
    mode_selector = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=mode_keys,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )
    defaults_schema = vol.Schema(
        {
            vol.Optional(
                CONF_MODE_DEFAULT,
                default=data.get(CONF_MODE_DEFAULT, DEFAULT_MODE_DEFAULT),
            ): mode_selector,
            vol.Optional(
                CONF_MODE_ABSENCE,
                default=data.get(CONF_MODE_ABSENCE, DEFAULT_MODE_ABSENCE),
            ): mode_selector,
            vol.Optional(
                CONF_MODE_WEEKEND,
                default=data.get(CONF_MODE_WEEKEND, DEFAULT_MODE_WEEKEND),
            ): mode_selector,
            vol.Optional(
                CONF_MODE_HOLIDAY,
                default=data.get(CONF_MODE_HOLIDAY, DEFAULT_MODE_HOLIDAY),
            ): mode_selector,
            vol.Optional(
                CONF_EVENT_MODE_MAP,
                default=data.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP),
            ): text,
        }
    )

    # Section 3: thermostat display names
    thermostat_fields_dict: dict = {}
    thermostat_fields_dict.update(_thermostat_display_fields(data))
    thermostat_schema = vol.Schema(thermostat_fields_dict)

    return vol.Schema(
        {
            vol.Required("day_modes_section"): section(day_modes_schema, {"collapsed": False}),
            vol.Required("defaults_section"): section(defaults_schema, {"collapsed": False}),
            vol.Required("thermostat_section"): section(thermostat_schema, {"collapsed": False}),
        }
    )


def _validate_calendars(hass, user_input: dict[str, Any]) -> dict[str, str]:
    """Return form errors for bad calendar entities."""
    errors: dict[str, str] = {}
    cal = user_input.get(CONF_CALENDAR_ENTITY)
    if cal and not hass.states.get(cal):
        errors[CONF_CALENDAR_ENTITY] = "invalid_calendar"
    hol = user_input.get(CONF_HOLIDAY_CALENDAR, "")
    if not hass.states.get(hol):
        errors[CONF_HOLIDAY_CALENDAR] = "invalid_calendar"
    return errors


def _parse_day_modes(data: dict[str, Any]) -> list[str]:
    """Return the list of configured day mode display values."""
    raw = data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP)
    return [v.strip() for v in _parse_day_mode_map(raw).values()]


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


def _covers_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build the cover heat-control form schema."""
    raw_lang = getattr(hass.config, "language", "en") if hasattr(hass, "config") else "en"
    lang = raw_lang.split("-")[0].lower()
    close_label = "Fermer les volets (close_cover)" if lang == "fr" else "Close Cover (close_cover)"
    stop_label = "Arrêter le mouvement (stop_cover)" if lang == "fr" else "Stop movement (stop_cover)"
    return vol.Schema(
        {
            vol.Optional(
                CONF_COVER_ENTITIES,
                default=data.get(CONF_COVER_ENTITIES, []),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="cover", multiple=True)),
            vol.Optional(
                CONF_COVER_TEMP_SENSOR,
                default=data.get(CONF_COVER_TEMP_SENSOR, ""),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(
                CONF_COVER_TEMP_THRESHOLD,
                default=data.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=60,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_COVER_MY_BUTTON,
                default=data.get(CONF_COVER_MY_BUTTON, ""),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="button")),
            vol.Optional(
                CONF_COVER_ACTION,
                default=data.get(CONF_COVER_ACTION, DEFAULT_COVER_ACTION),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "close_cover", "label": close_label},
                        {"value": "stop_cover", "label": stop_label},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_COVER_TIME_START,
                default=data.get(CONF_COVER_TIME_START, DEFAULT_COVER_TIME_START),
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_COVER_TIME_END,
                default=data.get(CONF_COVER_TIME_END, DEFAULT_COVER_TIME_END),
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_COVER_WEATHER_ENTITY,
                default=data.get(CONF_COVER_WEATHER_ENTITY, ""),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
            vol.Optional(
                CONF_COVER_FORECAST_THRESHOLD,
                default=data.get(CONF_COVER_FORECAST_THRESHOLD, DEFAULT_COVER_FORECAST_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=60,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_COVER_EVENING_REOPEN_TEMP,
                default=data.get(CONF_COVER_EVENING_REOPEN_TEMP, DEFAULT_COVER_EVENING_REOPEN_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=60,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _sunrise_schedulers_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build the sunrise-scheduler adjustment form schema."""
    sel = _scheduler_selector(hass)
    return vol.Schema(
        {
            vol.Optional(
                CONF_SUNRISE_SCHEDULERS,
                default=data.get(CONF_SUNRISE_SCHEDULERS, []),
            ): sel,
            vol.Optional(
                CONF_SUNRISE_EARLIEST,
                default=data.get(CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST),
            ): selector.TimeSelector(),
        }
    )


# ---------------------------------------------------------------------------
# Config flow (initial setup) – menu-based
# ---------------------------------------------------------------------------


class HomeShiftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeShift."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._data: dict[str, Any] = {}

    def is_matching(self, _other_flow: Self) -> bool:
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
        menu_options = ["calendars", "mapping", "schedulers", "covers", "sunrise_schedulers"]
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
            # Flatten section-nested input from the three sections
            flat: dict[str, Any] = {
                **user_input.get("day_modes_section", {}),
                **user_input.get("defaults_section", {}),
                **user_input.get("thermostat_section", {}),
            }
            flat[CONF_DAY_MODE_MAP] = _rebuild_day_mode_map(flat, self._effective_data())
            flat[CONF_THERMOSTAT_MODE_MAP] = _rebuild_thermostat_map(flat, self._effective_data())
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

    # -- covers ------------------------------------------------------------

    async def async_step_covers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure cover heat-control settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="covers",
            data_schema=_covers_schema(self.hass, self._effective_data()),
        )

    # -- sunrise schedulers ------------------------------------------------

    async def async_step_sunrise_schedulers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure sunrise-based scheduler adjustment."""
        if user_input is not None:
            value = user_input.get(CONF_SUNRISE_SCHEDULERS, [])
            if isinstance(value, str):
                value = [value] if value else []
            self._data[CONF_SUNRISE_SCHEDULERS] = value
            self._data[CONF_SUNRISE_EARLIEST] = user_input.get(
                CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST
            )
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="sunrise_schedulers",
            data_schema=_sunrise_schedulers_schema(self.hass, self._effective_data()),
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
        _config_entry: config_entries.ConfigEntry,
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
        self._data = {**self.config_entry.data, **self.config_entry.options}
        return await self.async_step_menu()

    # -- menu --------------------------------------------------------------

    async def async_step_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the options menu."""
        menu_options = ["calendars", "mapping", "schedulers", "covers", "sunrise_schedulers"]
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
            # Flatten section-nested input from the three sections
            flat: dict[str, Any] = {
                **user_input.get("day_modes_section", {}),
                **user_input.get("defaults_section", {}),
                **user_input.get("thermostat_section", {}),
            }
            flat[CONF_DAY_MODE_MAP] = _rebuild_day_mode_map(flat, self._effective_data())
            flat[CONF_THERMOSTAT_MODE_MAP] = _rebuild_thermostat_map(flat, self._effective_data())
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

    # -- covers ------------------------------------------------------------

    async def async_step_covers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure cover heat-control settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="covers",
            data_schema=_covers_schema(self.hass, self._effective_data()),
        )

    # -- sunrise schedulers ------------------------------------------------

    async def async_step_sunrise_schedulers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure sunrise-based scheduler adjustment."""
        if user_input is not None:
            value = user_input.get(CONF_SUNRISE_SCHEDULERS, [])
            if isinstance(value, str):
                value = [value] if value else []
            self._data[CONF_SUNRISE_SCHEDULERS] = value
            self._data[CONF_SUNRISE_EARLIEST] = user_input.get(
                CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST
            )
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="sunrise_schedulers",
            data_schema=_sunrise_schedulers_schema(self.hass, self._effective_data()),
        )

    # -- finalize ----------------------------------------------------------

    async def async_step_finalize(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Save options."""
        return self.async_create_entry(title="", data=self._data)
