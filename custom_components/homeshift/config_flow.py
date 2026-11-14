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
    CONF_ITEM_DAILY,
    CONF_ITEM_HEAT,
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
    CONF_AUTO_START_STOP_ITEMS,
    CONF_ITEM_CLIMATE,
    CONF_ITEM_SETPOINT_THRESHOLDS,
    CONF_ITEM_SWITCH,
    LOCALIZED_DEFAULTS,
    get_localized_defaults,
    parse_key_value_map,
)
from .auto_start_stop import default_climate, heat_pump_name
from .cover_manager import sun_time_at_elevation

_LOGGER = logging.getLogger(__name__)

# Shown after the summary of a menu entry whose section has unsaved changes.
PENDING_MARK = " ✎"

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


def _day_mode_display_fields(data: dict[str, Any], typed: dict[str, Any] | None = None) -> dict:
    """Return one TextSelector field per day mode key (key = label), prefilled with `typed` when given."""
    current_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    fields: dict = {}
    for key, display in current_map.items():
        field_name = f"day_display_{key.lower()}"
        fields[
            vol.Optional(
                field_name,
                default=(typed or {}).get(field_name, display),
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


def _thermostat_display_fields(data: dict[str, Any], typed: dict[str, Any] | None = None) -> dict:
    """Return one TextSelector field per thermostat key (key = label), prefilled with `typed` when given."""
    current_map = _parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))
    fields: dict = {}
    for key, display in current_map.items():
        field_name = f"thermostat_display_{key.lower()}"
        fields[
            vol.Optional(
                field_name,
                default=(typed or {}).get(field_name, display),
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


def _event_keyword_field(mode_key: str) -> str:
    """Form field holding the calendar keywords that switch the day to one mode."""
    return f"event_keywords_{mode_key.lower()}"


def _event_keywords_by_mode(data: dict[str, Any]) -> dict[str, str]:
    """Return the event keywords of each day mode key, comma separated.

    The stored map reads "Keyword:mode_key, ..."; a value naming a mode by its
    display name (written by hand) is matched back to its key.
    """
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    by_display = {display.lower(): key for key, display in day_mode_map.items()}
    keywords: dict[str, list[str]] = {key: [] for key in day_mode_map}
    for keyword, value in _parse_day_mode_map(data.get(CONF_EVENT_MODE_MAP, DEFAULT_EVENT_MODE_MAP)).items():
        key = value if value in keywords else by_display.get(value.lower())
        if key is not None:
            keywords[key].append(keyword)
    return {key: ", ".join(words) for key, words in keywords.items()}


def _rebuild_event_mode_map(user_input: dict[str, Any], data: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """Return the stored "Keyword:mode_key, ..." map built from the per-mode fields, and the errors.

    A keyword given for two modes would make the day's mode depend on the
    order of the list, so it is refused on the second field holding it.
    """
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    pairs: list[str] = []
    seen: set[str] = set()
    errors: dict[str, str] = {}
    for key in day_mode_map:
        field = _event_keyword_field(key)
        for keyword in str(user_input.pop(field, "") or "").split(","):
            keyword = keyword.strip().replace(":", "")
            if not keyword:
                continue
            if keyword.lower() in seen:
                errors[field] = "duplicate_keyword"
                continue
            seen.add(keyword.lower())
            pairs.append(f"{keyword}:{key}")
    return ", ".join(pairs), errors


def _mapping_schema(data: dict[str, Any]) -> vol.Schema:
    """Build the day mode form: which mode each kind of day gets, then the keywords per mode.

    The stored value of each rule is the mode key; the dropdown shows its
    display name. The keyword fields are labelled with the mode names
    (placeholders name_<key>).
    """
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
    rules_schema = vol.Schema(
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
        }
    )
    text = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))
    keywords = data.get("_keywords_draft") or _event_keywords_by_mode(data)
    keywords_schema = vol.Schema(
        {
            vol.Optional(
                _event_keyword_field(key),
                description={"suggested_value": keywords.get(key, "")},
            ): text
            for key in day_mode_map
        }
    )
    return vol.Schema(
        {
            vol.Required("defaults_section"): section(rules_schema, {"collapsed": False}),
            vol.Required("keywords_section"): section(keywords_schema, {"collapsed": False}),
        }
    )


MAPPING_SECTIONS = ("defaults_section", "keywords_section")


def _names_schema(data: dict[str, Any], typed: dict[str, Any] | None = None) -> vol.Schema:
    """Build the display names form: the day modes, then the thermostat modes."""
    return vol.Schema(
        {
            vol.Required("day_modes_section"): section(
                vol.Schema(_day_mode_display_fields(data, typed)), {"collapsed": False}
            ),
            vol.Required("thermostat_section"): section(
                vol.Schema(_thermostat_display_fields(data, typed)), {"collapsed": False}
            ),
        }
    )


NAMES_SECTIONS = ("day_modes_section", "thermostat_section")


def _validate_names(flat: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    """Refuse a display name the stored "key:name, ..." maps cannot hold.

    The maps are comma separated, so a comma would split a name ("Maison,
    repos" kept as "Maison"), an empty name would drop its mode, and two
    modes sharing a name could not be told apart (the current mode is
    stored by name). The error is reported on the whole form: the fields
    sit inside sections.
    """
    groups = (
        ("day_display_", _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))),
        ("thermostat_display_", _parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))),
    )
    for prefix, current_map in groups:
        seen: set[str] = set()
        for key, display in current_map.items():
            name = str(flat.get(f"{prefix}{key.lower()}", display) or "").strip()
            if not name or "," in name:
                return {"base": "invalid_mode_name"}
            if name.lower() in seen:
                return {"base": "duplicate_mode_name"}
            seen.add(name.lower())
    return {}


def _event_keywords_summary(data: dict[str, Any]) -> str:
    """Return "Keyword → mode name" for each calendar keyword, for the menu ("—" when none)."""
    day_mode_map = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
    return " · ".join(
        f"{keyword} → {day_mode_map.get(key, key)}"
        for key, words in _event_keywords_by_mode(data).items()
        for keyword in words.split(", ")
        if keyword
    ) or "—"


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


def _scheduler_climates(state: Any) -> set[str]:
    """Return the climates a Scheduler switch acts on (its entities, or its actions' targets)."""
    candidates: list[Any] = list(state.attributes.get("entities") or [])
    for action in state.attributes.get("actions") or []:
        if not isinstance(action, dict):
            continue
        for holder in (action, action.get("target") or {}):
            if isinstance(holder, dict):
                ids = holder.get("entity_id") or []
                candidates.extend([ids] if isinstance(ids, str) else ids)
    return {entity_id for entity_id in candidates if isinstance(entity_id, str) and entity_id.startswith("climate.")}


def _untagged_schedulers(hass, data: dict[str, Any]) -> list[str]:
    """Return the assigned schedules acting on a climate but tagged with no thermostat mode.

    Such a schedule runs whatever the thermostat mode, Off included: almost
    always a forgotten tag in the scheduler-card.
    """
    thermostat_tags = set(_parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP)).values())
    assigned: set[str] = set()
    for switches in (data.get(CONF_SCHEDULERS_PER_MODE, {}) or {}).values():
        assigned.update(switches or [])
    untagged = []
    for entity_id in sorted(assigned):
        state = hass.states.get(entity_id)
        if state is None or not _scheduler_climates(state):
            continue
        if not set(state.attributes.get("tags", []) or []) & thermostat_tags:
            untagged.append(_entity_name(hass, entity_id))
    return untagged


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

    What triggers the protection (temperature and forecast), then what it
    does to the covers; the covers themselves are ticked in the cover list.
    Option labels come from
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


def _open_at_sunrise_preview(hass, data: dict[str, Any]) -> dict[str, str]:
    """Return the next opening of a mode set to open at sunrise, for the form text.

    That is the next sunrise, held back to the "not before" time; '--:--'
    when the sun entity gives no sunrise.
    """
    state = hass.states.get("sun.sun")
    rising = dt_util.parse_datetime(str(state.attributes.get("next_rising") or "")) if state else None
    if rising is None:
        return {"open_at_sunrise": "--:--"}
    at = dt_util.as_local(rising).strftime("%H:%M")
    earliest = str(data.get(CONF_SUNRISE_EARLIEST, DEFAULT_SUNRISE_EARLIEST))[:5]
    return {"open_at_sunrise": max(at, earliest)}


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


def _heat_covers(data: dict[str, Any]) -> list[str]:
    """Return the covers protected from heat."""
    return [cover for cover in data.get(CONF_COVER_ENTITIES, []) or [] if cover]


def _all_covers(data: dict[str, Any]) -> list[str]:
    """Return every cover HomeShift drives: the daily ones first, then those only protected from heat."""
    covers = [item[CONF_ITEM_COVER] for item in _cover_items(data)]
    return covers + [cover for cover in _heat_covers(data) if cover not in covers]


def _cover_items_summary(data: dict[str, Any], name: Callable[[str], str] = str) -> str:
    """Return one line per cover for the menu description: what it does, its sensor and button.

    The roles are shown as symbols, explained by the translated text, so the
    line reads the same whatever the language. `name` turns an entity id
    into what the user sees; the flow passes the entity's friendly name.
    """
    covers = _all_covers(data)
    if not covers:
        return "—"
    items = {item[CONF_ITEM_COVER]: item for item in _cover_items(data)}
    heat = set(_heat_covers(data))
    lines = []
    for cover in covers:
        item = items.get(cover, {})
        roles = [symbol for symbol, on in (("🕒", cover in items), ("🌡️", cover in heat)) if on]
        line = f"- **{name(cover)}** {' '.join(roles)}"
        if item.get(CONF_ITEM_WINDOW_SENSOR):
            line += f" · 🪟 {name(item[CONF_ITEM_WINDOW_SENSOR])}"
        if item.get(CONF_ITEM_MY_BUTTON):
            line += f" · My: {name(item[CONF_ITEM_MY_BUTTON])}"
        lines.append(line)
    return "\n".join(lines)


def _cover_items_menu_options(data: dict[str, Any]) -> list[str]:
    """Return the individual-cover menu options (edit and remove once there's a cover)."""
    options = ["cover_item_add"]
    if _all_covers(data):
        options += ["cover_item_pick", "cover_item_remove"]
    options.append("covers_menu")
    return options


def _cover_roles_fields(daily: bool, heat: bool) -> dict:
    """Return the two role toggles of a cover: opened and closed every day, protected from heat."""
    return {
        vol.Optional(CONF_ITEM_DAILY, default=daily): selector.BooleanSelector(),
        vol.Optional(CONF_ITEM_HEAT, default=heat): selector.BooleanSelector(),
    }


def _cover_item_add_schema() -> vol.Schema:
    """Build the add-one-cover form schema."""
    return vol.Schema(
        {
            vol.Required(CONF_ITEM_COVER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="cover"),
            ),
            **_cover_roles_fields(True, False),
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
        for item in [{CONF_ITEM_COVER: cover} for cover in _all_covers(data)]
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


def _cover_item_edit_schema(item: dict[str, str], daily: bool, heat: bool) -> vol.Schema:
    """Build the edit-one-cover form, prefilled with its roles, window sensor and My button."""
    return vol.Schema(
        {
            **_cover_roles_fields(daily, heat),
            _entity_marker(
                CONF_ITEM_WINDOW_SENSOR, item.get(CONF_ITEM_WINDOW_SENSOR)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="binary_sensor")),
            _entity_marker(
                CONF_ITEM_MY_BUTTON, item.get(CONF_ITEM_MY_BUTTON)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="button")),
        }
    )


def _validate_cover_roles(user_input: dict[str, Any]) -> dict[str, str]:
    """Refuse a cover given no role: HomeShift would do nothing with it."""
    if not user_input.get(CONF_ITEM_DAILY, True) and not user_input.get(CONF_ITEM_HEAT, False):
        return {"base": "no_cover_role"}
    return {}


def _apply_cover_item_add(user_input: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Return the daily cover list and the heat-protected cover list with the submitted cover set.

    Re-adding a cover already configured updates it rather than duplicating
    it, so the add form doubles as the edit form.
    """
    cover = user_input.get(CONF_ITEM_COVER, "")
    daily = bool(user_input.get(CONF_ITEM_DAILY, True))
    heat = bool(user_input.get(CONF_ITEM_HEAT, False))
    sensor = user_input.get(CONF_ITEM_WINDOW_SENSOR, "") or ""
    button = user_input.get(CONF_ITEM_MY_BUTTON, "") or ""
    items = [dict(item) for item in _cover_items(data) if item[CONF_ITEM_COVER] != cover]
    position = next((i for i, item in enumerate(_cover_items(data)) if item[CONF_ITEM_COVER] == cover), len(items))
    if daily:
        items.insert(
            position, {CONF_ITEM_COVER: cover, CONF_ITEM_WINDOW_SENSOR: sensor, CONF_ITEM_MY_BUTTON: button}
        )
    heat_covers = [entity for entity in _heat_covers(data) if entity != cover]
    if heat:
        heat_covers.append(cover)
    return {CONF_DAILY_COVER_ITEMS: items, CONF_COVER_ENTITIES: heat_covers}


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


def _apply_cover_item_remove(user_input: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Return both cover lists without the covers selected for removal."""
    removed = user_input.get("remove_covers", []) or []
    if isinstance(removed, str):
        removed = [removed]
    return {
        CONF_DAILY_COVER_ITEMS: [item for item in _cover_items(data) if item[CONF_ITEM_COVER] not in removed],
        CONF_COVER_ENTITIES: [cover for cover in _heat_covers(data) if cover not in removed],
    }


# ---------------------------------------------------------------------------
# Climate auto start/stop
# ---------------------------------------------------------------------------


def _heat_pump_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the configured auto start/stop items (those naming a switch)."""
    raw = data.get(CONF_AUTO_START_STOP_ITEMS, []) or []
    return [item for item in raw if isinstance(item, dict) and item.get(CONF_ITEM_SWITCH)]


def _threshold_field(mode_key: str) -> str:
    """Form field holding the setpoint threshold of one thermostat mode."""
    return f"threshold_{mode_key.lower()}"


def _driven_thermostat_modes(data: dict[str, Any]) -> dict[str, str]:
    """Return the thermostat modes a threshold can be set for (key to display name): all but "off"."""
    modes = _parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))
    return {key: display for key, display in modes.items() if key.lower() != "off"}


def _thermostat_placeholders(data: dict[str, Any]) -> dict[str, str]:
    """Return each thermostat mode's display name, for the threshold labels (tname_<key>)."""
    return {f"tname_{key.lower()}": display for key, display in _driven_thermostat_modes(data).items()}


def _heat_pumps_summary(data: dict[str, Any], name: Callable[[str], str] = str) -> str:
    """Return one line per configured climate with the threshold of each thermostat mode
    it is driven in, for the menu text ("—" when there is none).
    """
    items = _heat_pump_items(data)
    if not items:
        return "—"
    modes = _driven_thermostat_modes(data)
    lines = []
    for item in items:
        thresholds = item.get(CONF_ITEM_SETPOINT_THRESHOLDS) or {}
        limits = []
        for key, display in modes.items():
            if thresholds.get(key) is not None:
                sign = "≥" if key.lower() == "heating" else "≤"
                limits.append(f"{display} {sign} {float(thresholds[key]):g} °C")
        lines.append(f"- **{heat_pump_name(name(item[CONF_ITEM_SWITCH]))}** · {', '.join(limits) or '—'}")
    return "\n".join(lines)


def _heat_pumps_menu_options(data: dict[str, Any]) -> list[str]:
    """Return the climate menu options (edit and remove once there's one)."""
    options = ["heat_pump_add"]
    if _heat_pump_items(data):
        options += ["heat_pump_pick", "heat_pump_remove"]
    options.append("menu")
    return options


def _heat_pump_schema(data: dict[str, Any], item: dict[str, Any] | None, *, with_switch: bool) -> vol.Schema:
    """Build the add (with_switch) or edit form of one climate, prefilled from `item`.

    One optional threshold per thermostat mode (empty: not driven in that
    mode), named after the mode's stable key.
    """
    item = item or {}
    thresholds = item.get(CONF_ITEM_SETPOINT_THRESHOLDS) or {}
    fields: dict = {}
    if with_switch:
        fields[_entity_marker(CONF_ITEM_SWITCH, item.get(CONF_ITEM_SWITCH), required=True)] = (
            selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))
        )
    fields[_entity_marker(CONF_ITEM_CLIMATE, item.get(CONF_ITEM_CLIMATE))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="climate")
    )
    for key in _driven_thermostat_modes(data):
        value = thresholds.get(key)
        fields[
            vol.Optional(
                _threshold_field(key),
                description={"suggested_value": value} if value is not None else None,
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5, max=35, step=0.5, unit_of_measurement="°C", mode=selector.NumberSelectorMode.BOX
            )
        )
    return vol.Schema(fields)


def _validate_heat_pump(user_input: dict[str, Any], data: dict[str, Any], switch: str | None = None) -> dict[str, str]:
    """Return the form errors: no threshold at all, no climate to read the setpoint from."""
    errors: dict[str, str] = {}
    if all(user_input.get(_threshold_field(key)) is None for key in _driven_thermostat_modes(data)):
        errors[_threshold_field(next(iter(_driven_thermostat_modes(data)), "heating"))] = "no_threshold"
    if not (user_input.get(CONF_ITEM_CLIMATE) or default_climate(switch or user_input.get(CONF_ITEM_SWITCH) or "")):
        errors[CONF_ITEM_CLIMATE] = "no_climate"
    return errors


def _apply_heat_pump(user_input: dict[str, Any], switch: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the items with this switch's settings added, or updated in place."""
    thresholds = {
        key: float(user_input[_threshold_field(key)])
        for key in _driven_thermostat_modes(data)
        if user_input.get(_threshold_field(key)) is not None
    }
    new = {
        CONF_ITEM_SWITCH: switch,
        CONF_ITEM_CLIMATE: user_input.get(CONF_ITEM_CLIMATE) or default_climate(switch),
        CONF_ITEM_SETPOINT_THRESHOLDS: thresholds,
    }
    items = [dict(item) for item in _heat_pump_items(data)]
    for index, item in enumerate(items):
        if item[CONF_ITEM_SWITCH] == switch:
            items[index] = new
            return items
    items.append(new)
    return items


def _configured_heat_pump_options(hass, data: dict[str, Any]) -> list[selector.SelectOptionDict]:
    """Return one option per configured switch, labelled with its friendly name."""
    return [
        selector.SelectOptionDict(value=item[CONF_ITEM_SWITCH], label=_entity_name(hass, item[CONF_ITEM_SWITCH]))
        for item in _heat_pump_items(data)
    ]


def _setpoint_text(hass, item: dict[str, Any] | None, switch: str) -> str:
    """Return the climate's current target temperature ("17.5 °C"), or "—" when it has none."""
    climate = (item or {}).get(CONF_ITEM_CLIMATE) or default_climate(switch)
    state = hass.states.get(climate) if climate else None
    try:
        return f"{float(state.attributes.get('temperature')):g} °C" if state else "—"
    except (TypeError, ValueError):
        return "—"


def _heat_pump_pick_schema(hass, data: dict[str, Any], *, field: str, multiple: bool) -> vol.Schema:
    """Build the form choosing configured switches (one to edit, several to remove)."""
    config = selector.SelectSelectorConfig(
        options=_configured_heat_pump_options(hass, data),
        multiple=multiple,
        mode=selector.SelectSelectorMode.LIST,
    )
    marker = vol.Optional(field, default=[]) if multiple else vol.Required(field)
    return vol.Schema({marker: selector.SelectSelector(config)})


# The sections of the flow, by step id, in menu order.
_PARTS = (
    "calendars",
    "mapping",
    "names",
    "schedulers",
    "cover_items",
    "daily_cover_schedule",
    "covers",
    "heat_pumps",
)

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
    # The switch being edited between heat_pump_pick and heat_pump_edit.
    _editing_switch: str
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

    def _menu_placeholders(self) -> dict[str, str]:
        """Return the summaries shown in the main menu and the covers menu.

        A section changed and not saved yet gets a marker after its summary
        (changed_<section>). The marker, unlike a section name, does not
        depend on a language: the flow cannot know the language of the
        person's profile, only that of the instance, so a translated name
        would not match the rest of the dialog.
        """
        data = self._effective_data()
        pending = set(self._pending_parts())
        changed = {f"changed_{part}": PENDING_MARK if part in pending else "" for part in _PARTS}
        changed["changed_covers_menu"] = (
            PENDING_MARK if pending & {"cover_items", "daily_cover_schedule", "covers"} else ""
        )
        modes = _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))
        schedulers: dict[str, list] = data.get(CONF_SCHEDULERS_PER_MODE, {}) or {}
        calendars = (data.get(CONF_CALENDAR_ENTITY), data.get(CONF_HOLIDAY_CALENDAR))
        try:
            threshold = f"{float(data.get(CONF_COVER_TEMP_THRESHOLD, DEFAULT_COVER_TEMP_THRESHOLD)):g}"
        except (TypeError, ValueError):
            threshold = "—"
        thermostat_modes = _parse_thermostat_map(data.get(CONF_THERMOSTAT_MODE_MAP, DEFAULT_THERMOSTAT_MODE_MAP))
        return changed | {
            "calendars": " · ".join(_entity_name(self.hass, cal) for cal in calendars if cal) or "—",
            "keywords": _event_keywords_summary(data),
            "modes": ", ".join(modes.values()),
            "thermostat_modes": ", ".join(thermostat_modes.values()),
            "pending_count": str(len(pending)),
            "scheduler_count": str(sum(len(value or []) for value in schedulers.values())),
            "cover_count": str(len(_all_covers(data))),
            "close_at": _close_time_preview(self.hass, data)["close_at_elevation"],
            "heat_cover_count": str(len(data.get(CONF_COVER_ENTITIES) or [])),
            "heat_threshold": threshold,
            "heat_pump_count": str(len(_heat_pump_items(data))),
        }

    # -- menus -------------------------------------------------------------

    async def async_step_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the configuration menu.

        Save comes first as soon as a section was changed, so it is not
        missed at the bottom of a long menu.
        """
        menu_options = ["calendars", "mapping", "schedulers", "covers_menu", "heat_pumps", "names"]
        if self._is_config_complete():
            if self._pending_parts():
                menu_options.insert(0, "finalize")
            else:
                menu_options.append("finalize")
        return self.async_show_menu(
            step_id="menu",
            menu_options=menu_options,
            description_placeholders=self._menu_placeholders(),
        )

    async def async_step_covers_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the covers menu: the managed covers, their schedule, heat protection."""
        return self.async_show_menu(
            step_id="covers_menu",
            menu_options=["cover_items", "daily_cover_schedule", "covers", "menu"],
            description_placeholders=self._menu_placeholders(),
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
        """Configure which mode each kind of day gets, and the calendar keywords of each mode."""
        data = self._effective_data()
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = _flatten_sections(user_input, MAPPING_SECTIONS)
            typed = {key: flat.get(_event_keyword_field(key), "") for key in _parse_day_mode_map(data.get(CONF_DAY_MODE_MAP, DEFAULT_DAY_MODE_MAP))}
            flat[CONF_EVENT_MODE_MAP], errors = _rebuild_event_mode_map(flat, data)
            if not errors:
                self._store("mapping", flat)
                return await self.async_step_menu()
            # Redisplay what was typed, so the keyword refused is there to correct.
            data = {**data, **{k: v for k, v in flat.items() if k != CONF_EVENT_MODE_MAP}, "_keywords_draft": typed}
            errors = {"base": "duplicate_keyword"}

        return self.async_show_form(
            step_id="mapping",
            data_schema=_mapping_schema(data),
            description_placeholders=_mode_placeholders(data),
            errors=errors,
        )

    # -- display names -------------------------------------------------------

    async def async_step_names(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Rename the day modes and the thermostat modes (their keys never change)."""
        data = self._effective_data()
        errors: dict[str, str] = {}
        typed: dict[str, Any] | None = None
        if user_input is not None:
            flat = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in _flatten_sections(user_input, NAMES_SECTIONS).items()
            }
            errors = _validate_names(flat, data)
            if not errors:
                flat[CONF_DAY_MODE_MAP] = _rebuild_day_mode_map(flat, data)
                flat[CONF_THERMOSTAT_MODE_MAP] = _rebuild_thermostat_map(flat, data)
                self._store("names", flat)
                return await self.async_step_menu()
            # Redisplay what was typed, so the refused name is there to correct.
            typed = flat

        return self.async_show_form(
            step_id="names",
            data_schema=_names_schema(data, typed),
            errors=errors,
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
            description_placeholders=_mode_placeholders(data)
            | {"untagged": ", ".join(_untagged_schedulers(self.hass, data)) or "—"},
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

        data = self._effective_data()
        return self.async_show_form(
            step_id="covers",
            data_schema=_covers_schema(self.hass, data),
            description_placeholders={
                "heat_covers": ", ".join(_entity_name(self.hass, cover) for cover in _heat_covers(data)) or "—"
            },
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
            description_placeholders=_close_time_preview(self.hass, data)
            | _open_at_sunrise_preview(self.hass, data)
            | _mode_placeholders(data),
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
        """Add one cover — or update one already configured."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_cover_roles(user_input)
            if not errors:
                self._store("cover_items", _apply_cover_item_add(user_input, self._data))
                return await self.async_step_cover_items()

        return self.async_show_form(
            step_id="cover_item_add",
            data_schema=_cover_item_add_schema(),
            errors=errors,
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
        """Change the roles, window sensor and My button of the cover being edited."""
        cover = self._editing_cover
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_cover_roles(user_input)
            if not errors:
                self._store("cover_items", _apply_cover_item_add({**user_input, CONF_ITEM_COVER: cover}, self._data))
                return await self.async_step_cover_items()

        item = next(
            (item for item in _cover_items(self._data) if item[CONF_ITEM_COVER] == cover),
            {CONF_ITEM_COVER: cover},
        )
        daily = any(entry[CONF_ITEM_COVER] == cover for entry in _cover_items(self._data))
        heat = cover in _heat_covers(self._data)
        return self.async_show_form(
            step_id="cover_item_edit",
            data_schema=_cover_item_edit_schema(item, daily, heat),
            description_placeholders={"cover": _entity_name(self.hass, cover)},
            errors=errors,
        )

    async def async_step_cover_item_remove(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Remove individually-configured covers."""
        if user_input is not None:
            self._store("cover_items", _apply_cover_item_remove(user_input, self._data))
            return await self.async_step_cover_items()

        return self.async_show_form(
            step_id="cover_item_remove",
            data_schema=_cover_item_remove_schema(self.hass, self._data),
        )


    # -- climate auto start/stop ----------------------------------------------

    async def async_step_heat_pumps(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the climate menu (add, edit, remove, or go back)."""
        return self.async_show_menu(
            step_id="heat_pumps",
            menu_options=_heat_pumps_menu_options(self._data),
            description_placeholders={
                "heat_pumps": _heat_pumps_summary(
                    self._effective_data(), lambda entity_id: _entity_name(self.hass, entity_id)
                )
            },
        )

    async def _async_heat_pump_form(
        self, step_id: str, user_input: dict[str, Any] | None, switch: str | None
    ) -> config_entries.ConfigFlowResult:
        """Show, validate and store the add (switch None) or edit form of one climate."""
        data = self._effective_data()
        errors: dict[str, str] = {}
        item = next((item for item in _heat_pump_items(data) if item[CONF_ITEM_SWITCH] == switch), None)
        if user_input is not None:
            errors = _validate_heat_pump(user_input, data, switch)
            if not errors:
                self._store(
                    "heat_pumps",
                    {
                        CONF_AUTO_START_STOP_ITEMS: _apply_heat_pump(
                            user_input, switch or user_input[CONF_ITEM_SWITCH], data
                        )
                    },
                )
                return await self.async_step_heat_pumps()
            # Redisplay what was typed, so the refused value is there to correct.
            item = {
                CONF_ITEM_SWITCH: switch or user_input.get(CONF_ITEM_SWITCH),
                CONF_ITEM_CLIMATE: user_input.get(CONF_ITEM_CLIMATE),
                CONF_ITEM_SETPOINT_THRESHOLDS: {
                    key: user_input.get(_threshold_field(key)) for key in _driven_thermostat_modes(data)
                },
            }
        placeholders = _thermostat_placeholders(data)
        if switch:
            placeholders["switch"] = _entity_name(self.hass, switch)
            placeholders["setpoint"] = _setpoint_text(self.hass, item, switch)
        return self.async_show_form(
            step_id=step_id,
            data_schema=_heat_pump_schema(data, item, with_switch=switch is None),
            description_placeholders=placeholders,
            errors=errors,
        )

    async def async_step_heat_pump_add(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Add one switch — or update one already configured."""
        return await self._async_heat_pump_form("heat_pump_add", user_input, None)

    async def async_step_heat_pump_pick(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose the configured switch to edit."""
        if user_input is not None:
            self._editing_switch = user_input[CONF_ITEM_SWITCH]
            return await self.async_step_heat_pump_edit()
        return self.async_show_form(
            step_id="heat_pump_pick",
            data_schema=_heat_pump_pick_schema(self.hass, self._data, field=CONF_ITEM_SWITCH, multiple=False),
        )

    async def async_step_heat_pump_edit(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Change the climate and the thresholds of the switch being edited."""
        return await self._async_heat_pump_form("heat_pump_edit", user_input, self._editing_switch)

    async def async_step_heat_pump_remove(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Stop driving some switches (the switches themselves are left as they are)."""
        if user_input is not None:
            removed = user_input.get("remove_switches", []) or []
            if isinstance(removed, str):
                removed = [removed]
            self._store(
                "heat_pumps",
                {
                    CONF_AUTO_START_STOP_ITEMS: [
                        item for item in _heat_pump_items(self._data) if item[CONF_ITEM_SWITCH] not in removed
                    ]
                },
            )
            return await self.async_step_heat_pumps()
        return self.async_show_form(
            step_id="heat_pump_remove",
            data_schema=_heat_pump_pick_schema(self.hass, self._data, field="remove_switches", multiple=True),
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
        self._editing_switch = ""

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
        return await self.async_step_calendars()

    async def async_step_menu(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Walk a first setup through two steps: the calendars, then the day mode rules.

        Everything else (schedules, covers, climates, names) is optional and
        set later from Configure, so a new user is not faced with the whole
        menu before HomeShift even runs.
        """
        if not self._is_config_complete():
            return await self.async_step_calendars()
        if "mapping" not in self._touched:
            return await self.async_step_mapping()
        return await self.async_step_finalize()

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
        self._editing_switch = ""

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
