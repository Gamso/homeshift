"""Config flow for HomeShift integration."""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any, Self

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

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
    CONF_COVER_ACTION,
    CONF_COVER_MY_BUTTON,
    DEFAULT_COVER_TEMP_THRESHOLD,
    DEFAULT_COVER_ACTION,
    CONF_COVER_WEATHER_ENTITY,
    CONF_COVER_FORECAST_THRESHOLD,
    DEFAULT_COVER_FORECAST_THRESHOLD,
    CONF_DAILY_COVER_ITEMS,
    CONF_ITEM_COVER,
    CONF_ITEM_WINDOW_SENSOR,
    CONF_ITEM_MY_BUTTON,
    CONF_DAILY_COVER_OPEN_TIME_MAP,
    CONF_DAILY_COVER_CLOSE_ELEVATION,
    CLOSE_ELEVATION_MIN,
    CLOSE_ELEVATION_MAX,
    DEFAULT_DAILY_COVER_OPEN_TIME,
    DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
    CONF_SUNRISE_EARLIEST,
    DEFAULT_SUNRISE_EARLIEST,
    CONF_CLOSE_WHEN_WINDOW_SHUTS,
    DEFAULT_CLOSE_WHEN_WINDOW_SHUTS,
    LOCALIZED_DEFAULTS,
    get_localized_defaults,
    parse_key_value_map,
)
from .cover_manager import sun_time_at_elevation

_LOGGER = logging.getLogger(__name__)

# Translation key of the per-mode opening time selector ('sunrise', 'skip').
DAILY_OPEN_TIME_SELECTOR = "daily_open_time"

# Aliases for backwards compatibility
_LOCALIZED_DEFAULTS = LOCALIZED_DEFAULTS
_get_localized_defaults = get_localized_defaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flatten_sections(user_input: dict[str, Any], sections: tuple[str, ...]) -> dict[str, Any]:
    """Return the form input with the fields of its collapsible sections lifted to the top.

    A section nests its fields under the section key in the submitted data;
    the stored options stay flat, so every step that groups its fields into
    sections flattens them first.
    """
    flat = {key: value for key, value in user_input.items() if key not in sections}
    for name in sections:
        flat.update(user_input.get(name) or {})
    return flat


def _entity_name(hass, entity_id: str) -> str:
    """Return an entity's friendly name, or its id when it has none (or is gone)."""
    state = hass.states.get(entity_id) if entity_id else None
    name = getattr(state, "name", None)
    return name if isinstance(name, str) and name else entity_id


def _entity_marker(key: str, value: Any, *, required: bool = False) -> vol.Marker:
    """Return a schema marker for an entity field that may currently be empty.

    An EntitySelector validates its value as an entity id, so a field carrying
    default="" renders with "Entity is neither a valid entity ID nor a valid
    UUID" before the user has touched anything. A stored value is offered as a
    suggestion instead — the frontend prefills it, but an untouched or cleared
    field simply stays out of the submitted data.
    """
    marker = vol.Required if required else vol.Optional
    if value:
        return marker(key, description={"suggested_value": value})
    return marker(key)


def _calendars_schema(data: dict[str, Any]) -> vol.Schema:
    """Build the calendars & schedule form schema."""
    return vol.Schema(
        {
            _entity_marker(
                CONF_CALENDAR_ENTITY, data.get(CONF_CALENDAR_ENTITY), required=True
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar"),
            ),
            _entity_marker(
                CONF_HOLIDAY_CALENDAR, data.get(CONF_HOLIDAY_CALENDAR), required=True
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar"),
            ),
        }
    )


def _parse_day_mode_map(map_str: str) -> dict[str, str]:
    """Parse 'Key:Display, ...' string into an ordered dict."""
    return parse_key_value_map(map_str)


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
    return parse_key_value_map(map_str)


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
    """Build the mode-mapping form schema with collapsible sections.

    The rules picking the day's mode come first and stay open; the display
    names, set once and rarely touched again, are folded away below them.
    """
    text = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))

    # Day mode display names (one field per key, like thermostat)
    day_fields_dict: dict = {}
    day_fields_dict.update(_day_mode_display_fields(data))
    day_modes_schema = vol.Schema(day_fields_dict)

    # Default mode assignments — the stored value is the mode key, the
    # dropdown shows its display name.
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    mode_selector = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=key, label=display)
                for key, display in day_mode_map.items()
            ],
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
                CONF_MODE_WEEKEND,
                default=data.get(CONF_MODE_WEEKEND, DEFAULT_MODE_WEEKEND),
            ): mode_selector,
            vol.Optional(
                CONF_MODE_HOLIDAY,
                default=data.get(CONF_MODE_HOLIDAY, DEFAULT_MODE_HOLIDAY),
            ): mode_selector,
            vol.Optional(
                CONF_MODE_ABSENCE,
                default=data.get(CONF_MODE_ABSENCE, DEFAULT_MODE_ABSENCE),
            ): mode_selector,
            vol.Optional(
                CONF_EVENT_MODE_MAP,
                default=data.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP),
            ): text,
        }
    )

    # Thermostat display names
    thermostat_fields_dict: dict = {}
    thermostat_fields_dict.update(_thermostat_display_fields(data))
    thermostat_schema = vol.Schema(thermostat_fields_dict)

    return vol.Schema(
        {
            vol.Required("defaults_section"): section(defaults_schema, {"collapsed": False}),
            vol.Required("day_modes_section"): section(day_modes_schema, {"collapsed": True}),
            vol.Required("thermostat_section"): section(thermostat_schema, {"collapsed": True}),
        }
    )


MAPPING_SECTIONS = ("defaults_section", "day_modes_section", "thermostat_section")


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


def _get_scheduler_options(hass) -> list[selector.SelectOptionDict]:
    """Return SelectSelector options for scheduler-like switch entities.

    Each option shows the scheduler's friendly name alone, so the chips stay
    short enough to read; the entity id is added back only to tell apart
    schedulers sharing the same name.
    """
    found = [
        (state.entity_id, state.attributes.get("friendly_name") or state.entity_id)
        for state in hass.states.async_all("switch")
        if "schedule" in state.entity_id.lower() or state.attributes.get("next_trigger") is not None
    ]
    names = [name for _, name in found]
    options: list[selector.SelectOptionDict] = [
        {
            "value": entity_id,
            "label": name if names.count(name) == 1 else f"{name} ({entity_id})",
        }
        for entity_id, name in found
    ]
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


def _scheduler_field(mode_key: str) -> str:
    """Return the form field name holding the schedulers of one day mode."""
    return f"schedulers_{mode_key.lower()}"


def _scheduler_section(mode_key: str) -> str:
    """Return the collapsible section grouping the schedulers of one day mode."""
    return f"mode_{mode_key.lower()}"


def _schedulers_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build scheduler form schema – one multi-select per day mode.

    Fields are named after the stable mode key (schedulers_home, ...), never
    after the display label: the label depends on the instance language and
    can be renamed, while the coordinator resolves schedulers by key. `data`
    must be the effective data (localized defaults included) so the form
    lists the modes the coordinator actually runs on.
    """
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    current_schedulers: dict[str, list] = data.get(CONF_SCHEDULERS_PER_MODE, {}) or {}
    sel = _scheduler_selector(hass)
    schema_dict: dict = {}
    for key in day_mode_map:
        current_value = current_schedulers.get(key, [])
        # One folded section per mode, titled with the mode's name and its
        # scheduler count, so the long chip lists open only on demand.
        schema_dict[vol.Required(_scheduler_section(key))] = section(
            vol.Schema({vol.Optional(_scheduler_field(key), default=current_value): sel}),
            {"collapsed": True},
        )
    return vol.Schema(schema_dict)


def _mode_placeholders(data: dict[str, Any]) -> dict[str, str]:
    """Return each day mode's display name and scheduler count, for the form text.

    Translations are keyed by the fixed mode keys; these placeholders put the
    names the user chose, and the number of schedulers behind each, into the
    labels and section titles.
    """
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    current_schedulers: dict[str, list] = data.get(CONF_SCHEDULERS_PER_MODE, {}) or {}
    placeholders: dict[str, str] = {}
    for key, display in day_mode_map.items():
        placeholders[f"name_{key.lower()}"] = display
        placeholders[f"count_{key.lower()}"] = str(len(current_schedulers.get(key, []) or []))
    return placeholders


def _extract_schedulers(user_input: dict[str, Any], data: dict[str, Any]) -> dict[str, list]:
    """Extract scheduler assignments from form user_input, keyed by day mode key."""
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    user_input = _flatten_sections(
        user_input, tuple(_scheduler_section(key) for key in day_mode_map)
    )
    result: dict[str, list] = {}
    for key in day_mode_map:
        value = user_input.get(_scheduler_field(key), [])
        if isinstance(value, str):
            value = [value] if value else []
        result[key] = list(value)
    return result


# Optional entity fields of the cover step: a cleared one is absent from the
# submitted data, so it has to be written back as "" rather than left at its
# previous value.
_CLEARABLE_COVER_ENTITIES = (
    CONF_COVER_TEMP_SENSOR,
    CONF_COVER_MY_BUTTON,
    CONF_COVER_WEATHER_ENTITY,
)


COVERS_SECTIONS = ("trigger_section", "action_section")


def _apply_covers_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return the cover-step input, flattened, with cleared entity fields set to empty."""
    user_input = _flatten_sections(user_input, COVERS_SECTIONS)
    return {key: user_input.get(key, "") for key in _CLEARABLE_COVER_ENTITIES} | user_input


def _covers_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build the cover heat-control form schema.

    The covers come first, then what triggers the protection (temperature
    and forecast), then what it does to the covers. Option labels come from
    the 'selector' section of the translations.
    """
    temperature = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=60,
            step=0.5,
            unit_of_measurement="°C",
            mode=selector.NumberSelectorMode.BOX,
        )
    )
    trigger_schema = vol.Schema(
        {
            _entity_marker(
                CONF_COVER_TEMP_SENSOR, data.get(CONF_COVER_TEMP_SENSOR)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(
                CONF_COVER_TEMP_THRESHOLD,
                default=data.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD),
            ): temperature,
            _entity_marker(
                CONF_COVER_WEATHER_ENTITY, data.get(CONF_COVER_WEATHER_ENTITY)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
            vol.Optional(
                CONF_COVER_FORECAST_THRESHOLD,
                default=data.get(CONF_COVER_FORECAST_THRESHOLD, DEFAULT_COVER_FORECAST_THRESHOLD),
            ): temperature,
        }
    )
    action_schema = vol.Schema(
        {
            _entity_marker(
                CONF_COVER_MY_BUTTON, data.get(CONF_COVER_MY_BUTTON)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="button")),
            vol.Optional(
                CONF_COVER_ACTION,
                default=data.get(CONF_COVER_ACTION, DEFAULT_COVER_ACTION),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["close_cover", "stop_cover"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_COVER_ACTION,
                )
            ),
        }
    )
    return vol.Schema(
        {
            vol.Optional(
                CONF_COVER_ENTITIES,
                default=data.get(CONF_COVER_ENTITIES, []),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="cover", multiple=True)),
            vol.Required("trigger_section"): section(trigger_schema, {"collapsed": False}),
            vol.Required("action_section"): section(action_schema, {"collapsed": False}),
        }
    )


def _daily_open_time_fields(data: dict[str, Any]) -> dict:
    """Return one open-time field per day mode key (key = label).

    Each field accepts 'sunrise', 'skip', or a custom 'HH:MM' value — letting
    every day mode be assigned its own opening behavior independently, so
    modes that should share a time are simply set to the same value.
    """
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    current_map = _parse_day_mode_map(data.get(CONF_DAILY_COVER_OPEN_TIME_MAP, ""))
    time_or_special_selector = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["sunrise", "skip"],
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
            translation_key=DAILY_OPEN_TIME_SELECTOR,
        )
    )
    fields: dict = {}
    for key in day_mode_map:
        field_name = f"daily_open_time_{key}"
        fields[
            vol.Optional(
                field_name,
                default=current_map.get(key, DEFAULT_DAILY_COVER_OPEN_TIME),
            )
        ] = time_or_special_selector
    return fields


def _rebuild_daily_open_time_map(user_input: dict[str, Any], data: dict[str, Any]) -> str:
    """Reconstruct CONF_DAILY_COVER_OPEN_TIME_MAP from individual per-mode fields."""
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    current_map = _parse_day_mode_map(data.get(CONF_DAILY_COVER_OPEN_TIME_MAP, ""))
    pairs: list[str] = []
    for key in day_mode_map:
        field_name = f"daily_open_time_{key}"
        value = user_input.pop(field_name, current_map.get(key, DEFAULT_DAILY_COVER_OPEN_TIME))
        pairs.append(f"{key}:{value}")
    return ", ".join(pairs)


def _close_elevation(data: dict[str, Any]) -> float:
    """Return the configured close elevation, falling back to the default."""
    try:
        return float(data.get(CONF_DAILY_COVER_CLOSE_ELEVATION, DEFAULT_DAILY_COVER_CLOSE_ELEVATION))
    except (TypeError, ValueError):
        return DEFAULT_DAILY_COVER_CLOSE_ELEVATION


def _close_time_preview(hass, data: dict[str, Any]) -> dict[str, str]:
    """Return tonight's closing time, ready for the form text.

    Degrees above the horizon say nothing about when the covers will move,
    so the step description turns the configured elevation into tonight's
    time, computed from the instance's own location. A time that cannot be
    computed (no location set, or an elevation the sun never reaches today)
    is rendered as '--:--'.
    """
    elevation = _close_elevation(data)
    at_elevation = sun_time_at_elevation(hass, elevation, dt_util.now().date())
    return {
        "close_elevation": f"{elevation:g}",
        "close_at_elevation": at_elevation.strftime("%H:%M") if at_elevation else "--:--",
    }


def _validate_close_elevation(hass, user_input: dict[str, Any]) -> dict[str, str]:
    """Reject an elevation the sun never reaches at this location.

    A threshold outside the sun's yearly range is a configuration mistake,
    not a fact of the night — above the polar circle, or a positive value at
    a high latitude in midwinter. Catching it here says so at once, instead
    of leaving the user to discover months later that the covers had been
    closing at sunset because the runtime kept falling back.

    The error is reported on the whole form: the field sits inside a
    section, and a field error there would need the section's nesting.
    """
    if CONF_DAILY_COVER_CLOSE_ELEVATION not in user_input:
        return {}

    elevation = _close_elevation(user_input)
    year = dt_util.now().year
    # The solstices bracket the year: the shortest night is the hardest day
    # for a threshold below the horizon, the lowest midday sun for one above.
    for solstice in (date(year, 6, 21), date(year, 12, 21)):
        if sun_time_at_elevation(hass, elevation, solstice) is None:
            return {"base": "elevation_unreachable"}
    return {}


DAILY_COVER_SECTIONS = ("close_section", "open_section")


def _daily_cover_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build the native daily cover open/close schedule form schema."""
    # The evening close and the morning open are two separate concerns, so
    # each gets its own section: the close elevation alone, then the sunrise
    # floor and the per-mode times.
    close_schema = vol.Schema({
        vol.Optional(
            CONF_DAILY_COVER_CLOSE_ELEVATION,
            default=_close_elevation(data),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=CLOSE_ELEVATION_MIN,
                max=CLOSE_ELEVATION_MAX,
                step=0.5,
                unit_of_measurement="°",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(
            CONF_CLOSE_WHEN_WINDOW_SHUTS,
            default=bool(data.get(CONF_CLOSE_WHEN_WINDOW_SHUTS, DEFAULT_CLOSE_WHEN_WINDOW_SHUTS)),
        ): selector.BooleanSelector(),
    })
    open_fields: dict = {
        vol.Optional(
            CONF_SUNRISE_EARLIEST,
            default=data.get(CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST),
        ): selector.TimeSelector(),
    }
    open_fields.update(_daily_open_time_fields(data))
    return vol.Schema(
        {
            vol.Required("close_section"): section(close_schema, {"collapsed": False}),
            vol.Required("open_section"): section(vol.Schema(open_fields), {"collapsed": False}),
        }
    )


# ---------------------------------------------------------------------------
# Individual covers (one cover + an optional window sensor, added one by one)
# ---------------------------------------------------------------------------


def _cover_items(data: dict[str, Any]) -> list[dict[str, str]]:
    """Return the configured individual covers, dropping malformed entries."""
    raw = data.get(CONF_DAILY_COVER_ITEMS, []) or []
    return [item for item in raw if isinstance(item, dict) and item.get(CONF_ITEM_COVER)]


def _cover_items_summary(data: dict[str, Any], name: Callable[[str], str] = str) -> str:
    """Return a human-readable list of the configured covers, for the menu description.

    `name` turns an entity id into what the user sees; the flow passes the
    entity's friendly name.
    """
    items = _cover_items(data)
    if not items:
        return "—"
    lines = []
    for item in items:
        sensor = item.get(CONF_ITEM_WINDOW_SENSOR, "")
        button = item.get(CONF_ITEM_MY_BUTTON, "")
        suffix = f" ← {name(sensor)}" if sensor else ""
        if button:
            suffix += f" (My: {name(button)})"
        lines.append(f"- **{name(item[CONF_ITEM_COVER])}**{suffix}")
    return "\n".join(lines)


def _cover_items_menu_options(data: dict[str, Any]) -> list[str]:
    """Return the individual-cover menu options (edit and remove once there's a cover)."""
    options = ["cover_item_add"]
    if _cover_items(data):
        options += ["cover_item_pick", "cover_item_remove"]
    options.append("covers_menu")
    return options


def _cover_item_add_schema() -> vol.Schema:
    """Build the add/update-one-cover form schema."""
    return vol.Schema(
        {
            vol.Required(CONF_ITEM_COVER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="cover"),
            ),
            vol.Optional(CONF_ITEM_WINDOW_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor"),
            ),
            vol.Optional(CONF_ITEM_MY_BUTTON): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="button"),
            ),
        }
    )


def _configured_cover_options(hass, data: dict[str, Any]) -> list[selector.SelectOptionDict]:
    """Return one option per configured cover, labelled with its friendly name."""
    return [
        selector.SelectOptionDict(
            value=item[CONF_ITEM_COVER], label=_entity_name(hass, item[CONF_ITEM_COVER])
        )
        for item in _cover_items(data)
    ]


def _cover_item_pick_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build the form choosing which configured cover to edit."""
    return vol.Schema(
        {
            vol.Required(CONF_ITEM_COVER): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_configured_cover_options(hass, data),
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _cover_item_edit_schema(item: dict[str, str]) -> vol.Schema:
    """Build the edit-one-cover form, prefilled with its window sensor and My button."""
    return vol.Schema(
        {
            _entity_marker(
                CONF_ITEM_WINDOW_SENSOR, item.get(CONF_ITEM_WINDOW_SENSOR)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="binary_sensor")),
            _entity_marker(
                CONF_ITEM_MY_BUTTON, item.get(CONF_ITEM_MY_BUTTON)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="button")),
        }
    )


def _apply_cover_item_add(user_input: dict[str, Any], data: dict[str, Any]) -> list[dict[str, str]]:
    """Return the cover list with the submitted cover added, or updated in place.

    Re-adding an already-configured cover updates its window sensor and My
    button rather than duplicating it, so the add form doubles as the edit form.
    """
    cover = user_input.get(CONF_ITEM_COVER, "")
    sensor = user_input.get(CONF_ITEM_WINDOW_SENSOR, "") or ""
    button = user_input.get(CONF_ITEM_MY_BUTTON, "") or ""
    items = [dict(item) for item in _cover_items(data)]
    for item in items:
        if item[CONF_ITEM_COVER] == cover:
            item[CONF_ITEM_WINDOW_SENSOR] = sensor
            item[CONF_ITEM_MY_BUTTON] = button
            return items
    items.append(
        {CONF_ITEM_COVER: cover, CONF_ITEM_WINDOW_SENSOR: sensor, CONF_ITEM_MY_BUTTON: button}
    )
    return items


def _cover_item_remove_schema(hass, data: dict[str, Any]) -> vol.Schema:
    """Build the remove-covers form schema (multi-select over configured covers)."""
    return vol.Schema(
        {
            vol.Optional("remove_covers", default=[]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_configured_cover_options(hass, data),
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _apply_cover_item_remove(user_input: dict[str, Any], data: dict[str, Any]) -> list[dict[str, str]]:
    """Return the cover list without the covers selected for removal."""
    removed = user_input.get("remove_covers", []) or []
    if isinstance(removed, str):
        removed = [removed]
    return [item for item in _cover_items(data) if item[CONF_ITEM_COVER] not in removed]


# The sections of the flow, by step id, in menu order.
_PARTS = ("calendars", "mapping", "schedulers", "cover_items", "daily_cover_schedule", "covers")

# What the cover forms prefill when nothing is stored yet: submitting them
# untouched writes these values, which is no change.
_COVER_FORM_DEFAULTS = {
    CONF_COVER_TEMP_THRESHOLD: DEFAULT_COVER_TEMP_THRESHOLD,
    CONF_COVER_ACTION: DEFAULT_COVER_ACTION,
    CONF_COVER_FORECAST_THRESHOLD: DEFAULT_COVER_FORECAST_THRESHOLD,
    CONF_DAILY_COVER_CLOSE_ELEVATION: DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
    CONF_SUNRISE_EARLIEST: DEFAULT_SUNRISE_EARLIEST,
    CONF_CLOSE_WHEN_WINDOW_SHUTS: DEFAULT_CLOSE_WHEN_WINDOW_SHUTS,
}


def _is_empty(value: Any) -> bool:
    """Return True for a value standing for "nothing set".

    A field never set and one cleared are the same, and so is a scheduler
    map listing no scheduler for any mode.
    """
    if isinstance(value, dict):
        return all(_is_empty(item) for item in value.values())
    return value in (None, "", [])


def _same_value(current: Any, initial: Any) -> bool:
    """Return True when a stored value has not really changed."""
    return current == initial or (_is_empty(current) and _is_empty(initial))


# ---------------------------------------------------------------------------
# Menu steps shared by the config flow and the options flow
# ---------------------------------------------------------------------------


class _HomeShiftMenuSteps:
    """The menu and its sections, identical in the config and options flows.

    Each flow keeps its own entry point (user / init) and final step
    (create the entry / save the options); everything in between edits
    self._data the same way.

    Nothing is saved before the final step, and closing the dialog drops
    every change, so the menu lists the sections changed so far: each step
    stores its input through _store(), which remembers the keys it touched.
    """

    hass: Any
    _data: dict[str, Any]
    # The data the flow started from, to tell a real change from a re-submit.
    _initial: dict[str, Any]
    # Keys written by each section, by the section's step id.
    _touched: dict[str, set[str]]
    # The cover being edited between cover_item_pick and cover_item_edit.
    _editing_cover: str
    # Translation category of the flow: "config" or "options".
    _translation_category: str

    def _effective_data(self) -> dict[str, Any]:
        """Return _data merged over localized defaults (for schema builders)."""
        return {**_get_localized_defaults(self.hass), **self._data}

    def _is_config_complete(self) -> bool:
        """Return True when the minimum required configuration is present."""
        return bool(self._data.get(CONF_CALENDAR_ENTITY))

    def _store(self, part: str, updates: dict[str, Any]) -> None:
        """Write a section's input into the flow data, remembering what it touched."""
        self._data.update(updates)
        self._touched.setdefault(part, set()).update(updates)

    def _pending_parts(self) -> list[str]:
        """Return the sections whose values differ from what the flow started with."""
        baseline = {**_COVER_FORM_DEFAULTS, **_get_localized_defaults(self.hass), **self._initial}
        if CONF_DAILY_COVER_OPEN_TIME_MAP not in baseline:
            baseline[CONF_DAILY_COVER_OPEN_TIME_MAP] = _rebuild_daily_open_time_map({}, baseline)
        return [
            part
            for part in _PARTS
            if any(
                not _same_value(self._data.get(key), baseline.get(key))
                for key in self._touched.get(part, ())
            )
        ]

    async def _part_labels(self) -> dict[str, str]:
        """Return each section's menu label, in the instance language."""
        category = self._translation_category
        translations = await async_get_translations(
            self.hass, self.hass.config.language, category, [DOMAIN]
        )
        labels: dict[str, str] = {}
        for menu in ("menu", "covers_menu"):
            prefix = f"component.{DOMAIN}.{category}.step.{menu}.menu_options."
            for part in _PARTS:
                if label := translations.get(prefix + part):
                    labels[part] = label
        return labels

    async def _menu_placeholders(self) -> dict[str, str]:
        """Return the summaries shown in the main menu and the covers menu."""
        data = self._effective_data()
        labels = await self._part_labels()
        modes = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
        schedulers: dict[str, list] = data.get(CONF_SCHEDULERS_PER_MODE, {}) or {}
        calendars = (data.get(CONF_CALENDAR_ENTITY), data.get(CONF_HOLIDAY_CALENDAR))
        try:
            threshold = f"{float(data.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD)):g}"
        except (TypeError, ValueError):
            threshold = "—"
        return {
            "pending": ", ".join(labels.get(part, part) for part in self._pending_parts()) or "—",
            "calendars": " · ".join(_entity_name(self.hass, cal) for cal in calendars if cal) or "—",
            "modes": ", ".join(modes.values()),
            "scheduler_count": str(sum(len(value or []) for value in schedulers.values())),
            "cover_count": str(len(_cover_items(data))),
            "close_at": _close_time_preview(self.hass, data)["close_at_elevation"],
            "heat_cover_count": str(len(data.get(CONF_COVER_ENTITIES) or [])),
            "heat_threshold": threshold,
        }

    # -- menus -------------------------------------------------------------

    async def async_step_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the configuration menu."""
        menu_options = ["calendars", "mapping", "schedulers", "covers_menu"]
        if self._is_config_complete():
            menu_options.append("finalize")
        return self.async_show_menu(
            step_id="menu",
            menu_options=menu_options,
            description_placeholders=await self._menu_placeholders(),
        )

    async def async_step_covers_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the covers menu: the managed covers, their schedule, heat protection."""
        return self.async_show_menu(
            step_id="covers_menu",
            menu_options=["cover_items", "daily_cover_schedule", "covers", "menu"],
            description_placeholders=await self._menu_placeholders(),
        )

    # -- calendars ---------------------------------------------------------

    async def async_step_calendars(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure the work and holiday calendar entities."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_calendars(self.hass, user_input)
            if not errors:
                self._store("calendars", user_input)
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
            flat = _flatten_sections(user_input, MAPPING_SECTIONS)
            flat[CONF_DAY_MODE_MAP] = _rebuild_day_mode_map(flat, self._effective_data())
            flat[CONF_THERMOSTAT_MODE_MAP] = _rebuild_thermostat_map(flat, self._effective_data())
            self._store("mapping", flat)
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
        data = self._effective_data()
        if user_input is not None:
            self._store(
                "schedulers", {CONF_SCHEDULERS_PER_MODE: _extract_schedulers(user_input, data)}
            )
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="schedulers",
            data_schema=_schedulers_schema(self.hass, data),
            description_placeholders=_mode_placeholders(data),
        )

    # -- covers ------------------------------------------------------------

    async def async_step_covers(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure cover heat-control settings."""
        if user_input is not None:
            self._store("covers", _apply_covers_input(user_input))
            return await self.async_step_covers_menu()

        return self.async_show_form(
            step_id="covers",
            data_schema=_covers_schema(self.hass, self._effective_data()),
        )

    # -- daily cover schedule ------------------------------------------------

    async def async_step_daily_cover_schedule(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure the native daily cover open/close schedule."""
        errors: dict[str, str] = {}
        data = self._effective_data()

        if user_input is not None:
            flat = _flatten_sections(user_input, DAILY_COVER_SECTIONS)
            errors = _validate_close_elevation(self.hass, flat)
            if not errors:
                flat[CONF_DAILY_COVER_OPEN_TIME_MAP] = _rebuild_daily_open_time_map(flat, data)
                self._store("daily_cover_schedule", flat)
                return await self.async_step_covers_menu()
            # Redisplay what was typed, not what is stored, so the rejected
            # value is there to correct and the preview matches it.
            data = {**data, **flat}
            data[CONF_DAILY_COVER_OPEN_TIME_MAP] = _rebuild_daily_open_time_map(dict(flat), data)

        return self.async_show_form(
            step_id="daily_cover_schedule",
            data_schema=_daily_cover_schema(self.hass, data),
            description_placeholders=_close_time_preview(self.hass, data) | _mode_placeholders(data),
            errors=errors,
        )

    # -- individual covers ---------------------------------------------------

    async def async_step_cover_items(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the individual-cover menu (add, edit, remove, or go back)."""
        return self.async_show_menu(
            step_id="cover_items",
            menu_options=_cover_items_menu_options(self._data),
            description_placeholders={
                "covers": _cover_items_summary(
                    self._data, lambda entity_id: _entity_name(self.hass, entity_id)
                )
            },
        )

    async def async_step_cover_item_add(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Add one cover — or update the window sensor of one already configured."""
        if user_input is not None:
            self._store(
                "cover_items", {CONF_DAILY_COVER_ITEMS: _apply_cover_item_add(user_input, self._data)}
            )
            return await self.async_step_cover_items()

        return self.async_show_form(
            step_id="cover_item_add",
            data_schema=_cover_item_add_schema(),
        )

    async def async_step_cover_item_pick(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose the configured cover to edit."""
        if user_input is not None:
            self._editing_cover = user_input[CONF_ITEM_COVER]
            return await self.async_step_cover_item_edit()

        return self.async_show_form(
            step_id="cover_item_pick",
            data_schema=_cover_item_pick_schema(self.hass, self._data),
        )

    async def async_step_cover_item_edit(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Change the window sensor and My button of the cover being edited."""
        cover = self._editing_cover
        if user_input is not None:
            self._store(
                "cover_items",
                {
                    CONF_DAILY_COVER_ITEMS: _apply_cover_item_add(
                        {**user_input, CONF_ITEM_COVER: cover}, self._data
                    )
                },
            )
            return await self.async_step_cover_items()

        item = next(
            (item for item in _cover_items(self._data) if item[CONF_ITEM_COVER] == cover),
            {CONF_ITEM_COVER: cover},
        )
        return self.async_show_form(
            step_id="cover_item_edit",
            data_schema=_cover_item_edit_schema(item),
            description_placeholders={"cover": _entity_name(self.hass, cover)},
        )

    async def async_step_cover_item_remove(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Remove individually-configured covers."""
        if user_input is not None:
            self._store(
                "cover_items",
                {CONF_DAILY_COVER_ITEMS: _apply_cover_item_remove(user_input, self._data)},
            )
            return await self.async_step_cover_items()

        return self.async_show_form(
            step_id="cover_item_remove",
            data_schema=_cover_item_remove_schema(self.hass, self._data),
        )


# ---------------------------------------------------------------------------
# Config flow (initial setup) – menu-based
# ---------------------------------------------------------------------------


class HomeShiftConfigFlow(_HomeShiftMenuSteps, config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeShift."""

    VERSION = 5
    _translation_category = "config"

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._data: dict[str, Any] = {}
        self._initial: dict[str, Any] = {}
        self._touched: dict[str, set[str]] = {}
        self._editing_cover = ""

    def is_matching(self, _other_flow: Self) -> bool:
        """Return True if another in-progress flow matches this one (not used)."""
        return False

    async def async_step_user(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Entry point – redirect to the menu, unless HomeShift is already set up.

        A second entry would mean a second coordinator driving the same covers
        and schedulers, each unaware of the other.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self.async_step_menu()

    async def async_step_finalize(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(title="HomeShift", data=self._data)

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


class HomeShiftOptionsFlow(_HomeShiftMenuSteps, config_entries.OptionsFlow):
    """Handle options flow for HomeShift."""

    _translation_category = "options"

    def __init__(self) -> None:
        """Initialize options flow."""
        self._data: dict[str, Any] = {}
        self._initial: dict[str, Any] = {}
        self._touched: dict[str, set[str]] = {}
        self._editing_cover = ""

    async def async_step_init(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Entry point – pre-populate from existing entry, then show menu."""
        self._data = {**self.config_entry.data, **self.config_entry.options}
        self._initial = dict(self._data)
        return await self.async_step_menu()

    async def async_step_finalize(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Save options."""
        return self.async_create_entry(title="", data=self._data)
