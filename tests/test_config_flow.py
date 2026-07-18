"""Tests for HomeShift's config_flow: schema builders, map (de)serialization, and step wiring."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import custom_components.homeshift.config_flow as cf
from custom_components.homeshift.const import (
    CONF_CALENDAR_ENTITY,
    CONF_COVER_ACTION,
    CONF_COVER_ENTITIES,
    CONF_COVER_TEMP_THRESHOLD,
    CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES,
    CONF_DAILY_COVER_ENTITIES,
    CONF_DAILY_COVER_OPEN_TIME_MAP,
    CONF_DAY_MODE_MAP,
    CONF_HOLIDAY_CALENDAR,
    CONF_SCHEDULERS_PER_MODE,
    CONF_SUNRISE_EARLIEST,
    DEFAULT_DAILY_COVER_OPEN_TIME,
    DEFAULT_DAY_MODE_MAP,
)


def _make_hass(language: str = "en", switch_states: list | None = None) -> MagicMock:
    """Return a MagicMock hass suitable for config_flow schema builders/steps."""
    hass = MagicMock()
    hass.config.language = language
    hass.states.async_all.return_value = switch_states or []
    hass.states.get.return_value = MagicMock()  # any entity_id "exists"
    return hass


# ---------------------------------------------------------------------------
# Day-mode map helpers (shared with covers' daily open-time map)
# ---------------------------------------------------------------------------

class TestParseDayModeMap:
    """_parse_day_mode_map: 'Key:Display, ...' -> ordered dict."""

    def test_parses_default_map(self):
        result = cf._parse_day_mode_map(DEFAULT_DAY_MODE_MAP)
        assert result == {"home": "Home", "work": "Work", "remote": "Remote", "away": "Away"}

    def test_ignores_entries_without_colon(self):
        result = cf._parse_day_mode_map("home:Home, garbage, work:Work")
        assert result == {"home": "Home", "work": "Work"}

    def test_empty_string_yields_empty_map(self):
        assert cf._parse_day_mode_map("") == {}


class TestRebuildDayModeMap:
    """_rebuild_day_mode_map: per-mode display fields -> 'Key:Display, ...' string, consuming fields."""

    def test_rebuilds_from_display_fields(self):
        data = {CONF_DAY_MODE_MAP: "home:Home, work:Work"}
        user_input = {"day_display_home": "Maison", "day_display_work": "Boulot"}
        result = cf._rebuild_day_mode_map(user_input, data)
        assert result == "home:Maison, work:Boulot"

    def test_falls_back_to_current_display_when_field_missing(self):
        data = {CONF_DAY_MODE_MAP: "home:Home, work:Work"}
        result = cf._rebuild_day_mode_map({}, data)
        assert result == "home:Home, work:Work"

    def test_pops_consumed_fields_from_user_input(self):
        data = {CONF_DAY_MODE_MAP: "home:Home"}
        user_input = {"day_display_home": "Maison"}
        cf._rebuild_day_mode_map(user_input, data)
        assert "day_display_home" not in user_input


# ---------------------------------------------------------------------------
# Daily cover open-time per-mode map (mirrors day-mode map pattern)
# ---------------------------------------------------------------------------

class TestDailyOpenTimeFields:
    """_daily_open_time_fields: one selector field per configured day-mode key."""

    def test_one_field_per_day_mode(self):
        data = {CONF_DAY_MODE_MAP: DEFAULT_DAY_MODE_MAP}
        fields = cf._daily_open_time_fields(data)
        field_names = {marker.schema for marker in fields}
        assert field_names == {
            "daily_open_time_home",
            "daily_open_time_work",
            "daily_open_time_remote",
            "daily_open_time_away",
        }

    def test_default_is_sunrise_when_no_current_map(self):
        data = {CONF_DAY_MODE_MAP: "home:Home"}
        fields = cf._daily_open_time_fields(data)
        (marker,) = fields.keys()
        assert marker.default() == DEFAULT_DAILY_COVER_OPEN_TIME

    def test_reflects_existing_map_value(self):
        data = {
            CONF_DAY_MODE_MAP: "home:Home, away:Away",
            CONF_DAILY_COVER_OPEN_TIME_MAP: "home:sunrise, away:skip",
        }
        fields = cf._daily_open_time_fields(data)
        defaults = {marker.schema: marker.default() for marker in fields}
        assert defaults["daily_open_time_home"] == "sunrise"
        assert defaults["daily_open_time_away"] == "skip"


class TestRebuildDailyOpenTimeMap:
    """_rebuild_daily_open_time_map: per-mode fields -> 'Key:Value, ...' string, consuming fields."""

    def test_rebuilds_from_user_input(self):
        data = {CONF_DAY_MODE_MAP: "home:Home, work:Work, away:Away"}
        user_input = {
            "daily_open_time_home": "08:30",
            "daily_open_time_work": "sunrise",
            "daily_open_time_away": "skip",
        }
        result = cf._rebuild_daily_open_time_map(user_input, data)
        assert result == "home:08:30, work:sunrise, away:skip"

    def test_falls_back_to_default_when_field_missing(self):
        data = {CONF_DAY_MODE_MAP: "home:Home"}
        result = cf._rebuild_daily_open_time_map({}, data)
        assert result == f"home:{DEFAULT_DAILY_COVER_OPEN_TIME}"

    def test_falls_back_to_existing_map_value_when_field_missing(self):
        data = {
            CONF_DAY_MODE_MAP: "home:Home, away:Away",
            CONF_DAILY_COVER_OPEN_TIME_MAP: "home:sunrise, away:skip",
        }
        result = cf._rebuild_daily_open_time_map({}, data)
        assert result == "home:sunrise, away:skip"

    def test_allows_custom_time_value(self):
        data = {CONF_DAY_MODE_MAP: "home:Home"}
        user_input = {"daily_open_time_home": "09:15"}
        result = cf._rebuild_daily_open_time_map(user_input, data)
        assert result == "home:09:15"

    def test_pops_consumed_fields_from_user_input(self):
        data = {CONF_DAY_MODE_MAP: "home:Home"}
        user_input = {"daily_open_time_home": "sunrise"}
        cf._rebuild_daily_open_time_map(user_input, data)
        assert "daily_open_time_home" not in user_input

    def test_away_mode_not_special_cased(self):
        """Away has no hardcoded default: it follows the map like any other mode (opens like Home unless configured otherwise)."""
        data = {CONF_DAY_MODE_MAP: "home:Home, away:Away"}
        result = cf._rebuild_daily_open_time_map({}, data)
        assert result == f"home:{DEFAULT_DAILY_COVER_OPEN_TIME}, away:{DEFAULT_DAILY_COVER_OPEN_TIME}"


# ---------------------------------------------------------------------------
# Schema builders
# ---------------------------------------------------------------------------

class TestCoversSchema:
    """_covers_schema: field set matches the close-only, native-schedule design."""

    def test_field_names(self):
        hass = _make_hass()
        schema = cf._covers_schema(hass, {})
        field_names = {marker.schema for marker in schema.schema}
        assert field_names == {
            "cover_entities",
            "cover_temp_sensor",
            "cover_temp_threshold",
            "cover_my_button",
            "cover_action",
            "cover_weather_entity",
            "cover_forecast_threshold",
        }

    def test_no_reopen_or_time_window_fields(self):
        """Old fields removed when heat protection became close-only & schedule-driven."""
        hass = _make_hass()
        schema = cf._covers_schema(hass, {})
        field_names = {marker.schema for marker in schema.schema}
        assert "cover_reopen_temp" not in field_names
        assert "cover_time_start" not in field_names
        assert "cover_time_end" not in field_names

    def test_french_action_labels(self):
        hass = _make_hass(language="fr")
        schema = cf._covers_schema(hass, {})
        action_marker = next(m for m in schema.schema if m.schema == CONF_COVER_ACTION)
        action_selector = schema.schema[action_marker]
        labels = {opt["label"] for opt in action_selector.config["options"]}
        assert "Fermer les volets (close_cover)" in labels

    def test_english_action_labels(self):
        hass = _make_hass(language="en")
        schema = cf._covers_schema(hass, {})
        action_marker = next(m for m in schema.schema if m.schema == CONF_COVER_ACTION)
        action_selector = schema.schema[action_marker]
        labels = {opt["label"] for opt in action_selector.config["options"]}
        assert "Close Cover (close_cover)" in labels

    def test_defaults_pulled_from_existing_data(self):
        hass = _make_hass()
        schema = cf._covers_schema(hass, {CONF_COVER_TEMP_THRESHOLD: 32.5})
        marker = next(m for m in schema.schema if m.schema == CONF_COVER_TEMP_THRESHOLD)
        assert marker.default() == 32.5


class TestDailyCoverSchema:
    """_daily_cover_schema: base fields + one open-time field per day mode."""

    def test_includes_base_and_per_mode_fields(self):
        hass = _make_hass()
        data = {CONF_DAY_MODE_MAP: DEFAULT_DAY_MODE_MAP}
        schema = cf._daily_cover_schema(hass, data)
        field_names = {marker.schema for marker in schema.schema}
        assert {
            CONF_DAILY_COVER_ENTITIES,
            CONF_SUNRISE_EARLIEST,
            CONF_DAILY_COVER_CLOSE_OFFSET_MINUTES,
            "daily_open_time_home",
            "daily_open_time_work",
            "daily_open_time_remote",
            "daily_open_time_away",
        }.issubset(field_names)

    def test_no_independent_heat_window_fields(self):
        """Heat window start/end were merged into this schedule; no separate config remains."""
        hass = _make_hass()
        schema = cf._daily_cover_schema(hass, {})
        field_names = {marker.schema for marker in schema.schema}
        assert "cover_time_start" not in field_names
        assert "cover_time_end" not in field_names


class TestValidateCalendars:
    """_validate_calendars: error keys for missing/invalid calendar entities."""

    def test_no_errors_when_both_exist(self):
        hass = _make_hass()
        errors = cf._validate_calendars(hass, {CONF_CALENDAR_ENTITY: "calendar.a", CONF_HOLIDAY_CALENDAR: "calendar.b"})
        assert errors == {}

    def test_error_when_calendar_missing(self):
        hass = MagicMock()
        hass.states.get.return_value = None
        errors = cf._validate_calendars(hass, {CONF_CALENDAR_ENTITY: "calendar.a", CONF_HOLIDAY_CALENDAR: "calendar.b"})
        assert errors[CONF_CALENDAR_ENTITY] == "invalid_calendar"
        assert errors[CONF_HOLIDAY_CALENDAR] == "invalid_calendar"

    def test_no_error_when_calendar_entity_blank(self):
        """CONF_CALENDAR_ENTITY is only validated if provided (falsy short-circuits the check)."""
        hass = MagicMock()
        hass.states.get.return_value = None
        errors = cf._validate_calendars(hass, {CONF_CALENDAR_ENTITY: "", CONF_HOLIDAY_CALENDAR: "calendar.b"})
        assert CONF_CALENDAR_ENTITY not in errors
        assert CONF_HOLIDAY_CALENDAR in errors


class TestSchedulerHelpers:
    """_get_scheduler_options / _scheduler_selector / _extract_schedulers."""

    def test_get_scheduler_options_filters_by_name_or_attribute(self):
        matching = MagicMock()
        matching.entity_id = "switch.schedule_volets"
        matching.attributes = {"friendly_name": "Volets"}
        non_matching = MagicMock()
        non_matching.entity_id = "switch.other"
        non_matching.attributes = {}
        hass = _make_hass(switch_states=[matching, non_matching])
        options = cf._get_scheduler_options(hass)
        assert len(options) == 1
        assert options[0]["value"] == "switch.schedule_volets"

    def test_extract_schedulers_normalizes_single_string_to_list(self):
        data = {CONF_DAY_MODE_MAP: "home:Home, work:Work"}
        user_input = {"Home": "switch.a", "Work": ["switch.b", "switch.c"]}
        result = cf._extract_schedulers(user_input, data)
        assert result == {"Home": ["switch.a"], "Work": ["switch.b", "switch.c"]}

    def test_extract_schedulers_defaults_missing_mode_to_empty_list(self):
        data = {CONF_DAY_MODE_MAP: "home:Home, work:Work"}
        result = cf._extract_schedulers({}, data)
        assert result == {"Home": [], "Work": []}

    def test_scheduler_selector_uses_select_when_matches_found(self):
        matching = MagicMock()
        matching.entity_id = "switch.schedule_volets"
        matching.attributes = {"friendly_name": "Volets"}
        hass = _make_hass(switch_states=[matching])
        sel = cf._scheduler_selector(hass)
        assert isinstance(sel, type(cf.selector.SelectSelector(cf.selector.SelectSelectorConfig(options=[]))))

    def test_scheduler_selector_falls_back_to_entity_selector_when_no_matches(self):
        hass = _make_hass(switch_states=[])
        sel = cf._scheduler_selector(hass)
        assert isinstance(sel, cf.selector.EntitySelector)


class TestMappingSchema:
    """_mapping_schema: three collapsible sections (day modes, defaults, thermostat)."""

    def test_has_three_sections(self):
        data = {CONF_DAY_MODE_MAP: DEFAULT_DAY_MODE_MAP}
        schema = cf._mapping_schema(data)
        section_names = {marker.schema for marker in schema.schema}
        assert section_names == {"day_modes_section", "defaults_section", "thermostat_section"}


# ---------------------------------------------------------------------------
# ConfigFlow step wiring
# ---------------------------------------------------------------------------

class TestConfigFlowMenu:
    """async_step_menu: options offered, 'finalize' gated on minimum config."""

    async def test_user_step_redirects_to_menu(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_user()
        assert result["step_id"] == "menu"

    async def test_finalize_absent_when_incomplete(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_menu()
        assert result["menu_options"] == ["calendars", "mapping", "schedulers", "covers", "daily_cover_schedule"]

    async def test_finalize_present_once_calendar_configured(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_CALENDAR_ENTITY] = "calendar.a"
        result = await flow.async_step_menu()
        assert result["menu_options"][-1] == "finalize"


class TestConfigFlowCalendarsStep:
    """async_step_calendars: validates, stores, and returns to the menu."""

    async def test_valid_input_updates_data_and_returns_to_menu(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_calendars({CONF_CALENDAR_ENTITY: "calendar.a", CONF_HOLIDAY_CALENDAR: "calendar.b"})
        assert result["step_id"] == "menu"
        assert flow._data[CONF_CALENDAR_ENTITY] == "calendar.a"

    async def test_invalid_input_redisplays_form_with_errors(self):
        flow = cf.HomeShiftConfigFlow()
        hass = MagicMock()
        hass.states.get.return_value = None
        flow.hass = hass
        result = await flow.async_step_calendars({CONF_CALENDAR_ENTITY: "calendar.a", CONF_HOLIDAY_CALENDAR: "calendar.b"})
        assert result["step_id"] == "calendars"
        assert result["errors"]
        assert CONF_CALENDAR_ENTITY not in flow._data


class TestConfigFlowCoversStep:
    """async_step_covers: stores whatever fields the form submits verbatim."""

    async def test_stores_submitted_fields(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_covers({CONF_COVER_ENTITIES: ["cover.salon"], CONF_COVER_ACTION: "stop_cover"})
        assert result["step_id"] == "menu"
        assert flow._data[CONF_COVER_ENTITIES] == ["cover.salon"]
        assert flow._data[CONF_COVER_ACTION] == "stop_cover"

    async def test_shows_form_when_no_input(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_covers()
        assert result["step_id"] == "covers"


class TestConfigFlowMappingSchedulersShowForm:
    """Steps that only build+return a form when called with no input."""

    async def test_mapping_shows_form(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_mapping()
        assert result["step_id"] == "mapping"

    async def test_schedulers_shows_form(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_schedulers()
        assert result["step_id"] == "schedulers"

    async def test_daily_cover_schedule_shows_form(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_daily_cover_schedule()
        assert result["step_id"] == "daily_cover_schedule"

    async def test_calendars_shows_form_with_no_input(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_calendars()
        assert result["step_id"] == "calendars"


class TestConfigFlowDailyCoverScheduleStep:
    """async_step_daily_cover_schedule: rebuilds the per-mode open-time map before storing."""

    async def test_rebuilds_open_time_map_into_data(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home, away:Away"
        result = await flow.async_step_daily_cover_schedule(
            {
                CONF_DAILY_COVER_ENTITIES: ["cover.volets"],
                "daily_open_time_home": "sunrise",
                "daily_open_time_away": "skip",
            }
        )
        assert result["step_id"] == "menu"
        assert flow._data[CONF_DAILY_COVER_OPEN_TIME_MAP] == "home:sunrise, away:skip"
        assert flow._data[CONF_DAILY_COVER_ENTITIES] == ["cover.volets"]

    async def test_per_mode_fields_not_leaked_into_stored_data(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"
        await flow.async_step_daily_cover_schedule({"daily_open_time_home": "08:30"})
        assert "daily_open_time_home" not in flow._data


class TestConfigFlowMappingStep:
    """async_step_mapping: flattens the three sections and rebuilds both maps."""

    async def test_flattens_sections_and_rebuilds_maps(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        user_input = {
            "day_modes_section": {"day_display_home": "Maison"},
            "defaults_section": {},
            "thermostat_section": {},
        }
        result = await flow.async_step_mapping(user_input)
        assert result["step_id"] == "menu"
        assert "home:Maison" in flow._data[CONF_DAY_MODE_MAP]


class TestConfigFlowSchedulersStep:
    """async_step_schedulers: extracts per-mode scheduler assignments."""

    async def test_stores_extracted_schedulers(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"
        result = await flow.async_step_schedulers({"Home": "switch.a"})
        assert result["step_id"] == "menu"
        assert flow._data[CONF_SCHEDULERS_PER_MODE] == {"Home": ["switch.a"]}


class TestConfigFlowFinalize:
    """async_step_finalize: creates the config entry with the accumulated data."""

    async def test_creates_entry_with_accumulated_data(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_CALENDAR_ENTITY] = "calendar.a"
        result = await flow.async_step_finalize()
        assert result["title"] == "HomeShift"
        assert result["data"][CONF_CALENDAR_ENTITY] == "calendar.a"

    def test_options_flow_accessor_returns_options_flow(self):
        flow_handler = cf.HomeShiftConfigFlow.async_get_options_flow(MagicMock())
        assert isinstance(flow_handler, cf.HomeShiftOptionsFlow)


# ---------------------------------------------------------------------------
# OptionsFlow step wiring
# ---------------------------------------------------------------------------

def _make_options_flow(entry_data: dict, entry_options: dict | None = None) -> cf.HomeShiftOptionsFlow:
    """Build a HomeShiftOptionsFlow with hass/handler wired for the config_entry property."""
    flow = cf.HomeShiftOptionsFlow()
    hass = _make_hass()
    entry = MagicMock()
    entry.data = entry_data
    entry.options = entry_options or {}
    hass.config_entries.async_get_known_entry.return_value = entry
    flow.hass = hass
    flow.handler = "test_entry"
    return flow


class TestOptionsFlowInit:
    """async_step_init: pre-populates _data from the existing entry before showing the menu."""

    async def test_prepopulates_from_entry_and_shows_menu(self):
        flow = _make_options_flow({CONF_CALENDAR_ENTITY: "calendar.a"})
        result = await flow.async_step_init()
        assert result["step_id"] == "menu"
        assert flow._data[CONF_CALENDAR_ENTITY] == "calendar.a"
        assert result["menu_options"][-1] == "finalize"

    async def test_options_override_entry_data(self):
        flow = _make_options_flow({CONF_COVER_TEMP_THRESHOLD: 30.0}, entry_options={CONF_COVER_TEMP_THRESHOLD: 32.0})
        await flow.async_step_init()
        assert flow._data[CONF_COVER_TEMP_THRESHOLD] == 32.0


class TestOptionsFlowDailyCoverScheduleStep:
    """Same rebuild-map behavior as the config flow's step."""

    async def test_rebuilds_open_time_map(self):
        flow = _make_options_flow({CONF_DAY_MODE_MAP: "home:Home, away:Away"})
        await flow.async_step_init()
        result = await flow.async_step_daily_cover_schedule(
            {"daily_open_time_home": "08:30", "daily_open_time_away": "skip"}
        )
        assert result["step_id"] == "menu"
        assert flow._data[CONF_DAILY_COVER_OPEN_TIME_MAP] == "home:08:30, away:skip"


class TestOptionsFlowFinalize:
    """async_step_finalize: saves accumulated _data as the entry's options."""

    async def test_saves_data_as_options(self):
        flow = _make_options_flow({CONF_CALENDAR_ENTITY: "calendar.a"})
        await flow.async_step_init()
        result = await flow.async_step_finalize()
        assert result["title"] == ""
        assert result["data"][CONF_CALENDAR_ENTITY] == "calendar.a"


class TestOptionsFlowShowForms:
    """Each step mirrors the config flow's: shows its form when called with no input."""

    async def test_calendars_shows_form(self):
        flow = _make_options_flow({})
        await flow.async_step_init()
        result = await flow.async_step_calendars()
        assert result["step_id"] == "calendars"

    async def test_calendars_invalid_input_shows_errors(self):
        flow = _make_options_flow({})
        flow.hass.states.get.return_value = None
        await flow.async_step_init()
        result = await flow.async_step_calendars({CONF_CALENDAR_ENTITY: "calendar.a", CONF_HOLIDAY_CALENDAR: "calendar.b"})
        assert result["step_id"] == "calendars"
        assert result["errors"]

    async def test_mapping_shows_form_and_accepts_input(self):
        flow = _make_options_flow({CONF_DAY_MODE_MAP: DEFAULT_DAY_MODE_MAP})
        await flow.async_step_init()
        form = await flow.async_step_mapping()
        assert form["step_id"] == "mapping"
        result = await flow.async_step_mapping(
            {"day_modes_section": {}, "defaults_section": {}, "thermostat_section": {}}
        )
        assert result["step_id"] == "menu"

    async def test_schedulers_shows_form_and_accepts_input(self):
        flow = _make_options_flow({CONF_DAY_MODE_MAP: "home:Home"})
        await flow.async_step_init()
        form = await flow.async_step_schedulers()
        assert form["step_id"] == "schedulers"
        result = await flow.async_step_schedulers({"Home": "switch.a"})
        assert result["step_id"] == "menu"
        assert flow._data[CONF_SCHEDULERS_PER_MODE] == {"Home": ["switch.a"]}

    async def test_covers_shows_form_and_accepts_input(self):
        flow = _make_options_flow({})
        await flow.async_step_init()
        form = await flow.async_step_covers()
        assert form["step_id"] == "covers"
        result = await flow.async_step_covers({CONF_COVER_ENTITIES: ["cover.a"]})
        assert result["step_id"] == "menu"
        assert flow._data[CONF_COVER_ENTITIES] == ["cover.a"]

    async def test_daily_cover_schedule_shows_form(self):
        flow = _make_options_flow({CONF_DAY_MODE_MAP: "home:Home"})
        await flow.async_step_init()
        form = await flow.async_step_daily_cover_schedule()
        assert form["step_id"] == "daily_cover_schedule"
