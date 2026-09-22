"""Tests for HomeShift's config_flow: schema builders, map (de)serialization, and step wiring."""
from __future__ import annotations

import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol

import custom_components.homeshift.config_flow as cf
from custom_components.homeshift.const import (
    CLOSE_ELEVATION_MAX,
    CLOSE_ELEVATION_MIN,
    CONF_CALENDAR_ENTITY,
    CONF_COVER_ACTION,
    CONF_COVER_ENTITIES,
    CONF_COVER_TEMP_SENSOR,
    CONF_COVER_TEMP_THRESHOLD,
    CONF_DAILY_COVER_CLOSE_ELEVATION,
    CONF_DAILY_COVER_ITEMS,
    CONF_ITEM_COVER,
    CONF_DAILY_COVER_OPEN_TIME_MAP,
    CONF_DAY_MODE_MAP,
    CONF_HOLIDAY_CALENDAR,
    CONF_SCHEDULERS_PER_MODE,
    CONF_SUNRISE_EARLIEST,
    DEFAULT_DAILY_COVER_CLOSE_ELEVATION,
    DEFAULT_DAILY_COVER_OPEN_TIME,
    DEFAULT_DAY_MODE_MAP,
)


def _make_hass(language: str = "en", switch_states: list | None = None) -> MagicMock:
    """Return a MagicMock hass suitable for config_flow schema builders/steps."""
    hass = MagicMock()
    hass.config.language = language
    hass.states.async_all.return_value = switch_states or []
    hass.states.get.return_value = MagicMock()  # any entity_id "exists"
    hass.config_entries.async_entries.return_value = []  # nothing configured yet
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
            CONF_SUNRISE_EARLIEST,
            CONF_DAILY_COVER_CLOSE_ELEVATION,
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

    async def test_user_step_aborts_when_already_configured(self):
        """A second entry would mean two coordinators driving the same covers."""
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow.hass.config_entries.async_entries.return_value = [MagicMock()]
        result = await flow.async_step_user()
        assert result["type"] == "abort"
        assert result["reason"] == "single_instance_allowed"

    async def test_finalize_absent_when_incomplete(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_menu()
        assert result["menu_options"] == ["calendars", "mapping", "schedulers", "covers", "daily_cover_schedule", "cover_items"]

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
                "daily_open_time_home": "sunrise",
                "daily_open_time_away": "skip",
            }
        )
        assert result["step_id"] == "menu"
        assert flow._data[CONF_DAILY_COVER_OPEN_TIME_MAP] == "home:sunrise, away:skip"

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
# ---------------------------------------------------------------------------
# Individual covers (add / remove one cover + its optional window sensor)
# ---------------------------------------------------------------------------

class TestCoverItemHelpers:
    """_cover_items* helpers: normalize, summarize, add/update and remove."""

    def test_drops_entries_without_a_cover(self):
        data = {CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a"}, {"window_sensor": "binary_sensor.b"}, "junk"]}
        assert cf._cover_items(data) == [{"cover": "cover.a"}]

    def test_summary_lists_each_cover_with_its_sensor(self):
        data = {
            CONF_DAILY_COVER_ITEMS: [
                {"cover": "cover.a", "window_sensor": "binary_sensor.b"},
                {"cover": "cover.c", "window_sensor": ""},
            ]
        }
        summary = cf._cover_items_summary(data)
        assert "cover.a" in summary and "binary_sensor.b" in summary
        assert summary.splitlines()[-1].strip() == "- cover.c"

    def test_summary_shows_the_my_button(self):
        data = {CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": "", "my_button": "button.my_a"}]}
        assert cf._cover_items_summary(data) == "- cover.a (My: button.my_a)"

    def test_summary_when_nothing_configured(self):
        assert cf._cover_items_summary({}) == "—"

    def test_menu_offers_remove_only_when_covers_exist(self):
        assert cf._cover_items_menu_options({}) == ["cover_item_add", "menu"]
        assert cf._cover_items_menu_options({CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a"}]}) == [
            "cover_item_add",
            "cover_item_remove",
            "menu",
        ]

    def test_add_appends_a_new_cover(self):
        data = {CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": ""}]}
        result = cf._apply_cover_item_add({"cover": "cover.b", "window_sensor": "binary_sensor.b"}, data)
        assert result == [
            {"cover": "cover.a", "window_sensor": ""},
            {"cover": "cover.b", "window_sensor": "binary_sensor.b", "my_button": ""},
        ]

    def test_re_adding_a_cover_updates_its_sensor_instead_of_duplicating(self):
        data = {CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": "binary_sensor.old"}]}
        result = cf._apply_cover_item_add({"cover": "cover.a", "window_sensor": "binary_sensor.new"}, data)
        assert result == [{"cover": "cover.a", "window_sensor": "binary_sensor.new", "my_button": ""}]

    def test_re_adding_a_cover_updates_its_my_button(self):
        data = {CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": "", "my_button": "button.old"}]}
        result = cf._apply_cover_item_add({"cover": "cover.a", "my_button": "button.new"}, data)
        assert result == [{"cover": "cover.a", "window_sensor": "", "my_button": "button.new"}]

    def test_add_stores_the_my_button(self):
        result = cf._apply_cover_item_add({"cover": "cover.a", "my_button": "button.my_a"}, {})
        assert result == [{"cover": "cover.a", "window_sensor": "", "my_button": "button.my_a"}]

    def test_add_without_a_sensor_stores_an_empty_string(self):
        result = cf._apply_cover_item_add({"cover": "cover.a"}, {})
        assert result == [{"cover": "cover.a", "window_sensor": "", "my_button": ""}]

    def test_remove_drops_the_selected_covers(self):
        data = {
            CONF_DAILY_COVER_ITEMS: [
                {"cover": "cover.a", "window_sensor": ""},
                {"cover": "cover.b", "window_sensor": ""},
            ]
        }
        assert cf._apply_cover_item_remove({"remove_covers": ["cover.a"]}, data) == [
            {"cover": "cover.b", "window_sensor": ""}
        ]

    def test_remove_with_nothing_selected_keeps_everything(self):
        data = {CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": ""}]}
        assert cf._apply_cover_item_remove({}, data) == [{"cover": "cover.a", "window_sensor": ""}]

    def test_add_schema_has_a_required_cover_and_two_optional_fields(self):
        schema = cf._cover_item_add_schema()
        markers = {marker.schema: marker for marker in schema.schema}
        assert set(markers) == {"cover", "window_sensor", "my_button"}
        assert isinstance(markers["cover"], vol.Required)
        assert isinstance(markers["window_sensor"], vol.Optional)
        assert isinstance(markers["my_button"], vol.Optional)

    def test_remove_schema_offers_every_configured_cover(self):
        data = {
            CONF_DAILY_COVER_ITEMS: [
                {"cover": "cover.a", "window_sensor": "binary_sensor.b"},
                {"cover": "cover.c", "window_sensor": ""},
            ]
        }
        schema = cf._cover_item_remove_schema(data)
        (marker,) = schema.schema
        assert marker.schema == "remove_covers"
        options = schema.schema[marker].config["options"]
        assert [option["value"] for option in options] == ["cover.a", "cover.c"]


class TestConfigFlowCoverItemSteps:
    """async_step_cover_item*: menu, add and remove all return to the cover-item menu."""

    async def test_menu_lists_configured_covers(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_DAILY_COVER_ITEMS] = [{"cover": "cover.a", "window_sensor": "binary_sensor.b"}]
        result = await flow.async_step_cover_items()
        assert result["step_id"] == "cover_items"
        assert result["menu_options"] == ["cover_item_add", "cover_item_remove", "menu"]
        assert "cover.a" in result["description_placeholders"]["covers"]

    async def test_add_shows_form_then_stores_the_cover(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        form = await flow.async_step_cover_item_add()
        assert form["step_id"] == "cover_item_add"

        result = await flow.async_step_cover_item_add(
            {"cover": "cover.chambre", "window_sensor": "binary_sensor.fenetre_chambre"}
        )
        assert result["step_id"] == "cover_items"
        assert flow._data[CONF_DAILY_COVER_ITEMS] == [
            {"cover": "cover.chambre", "window_sensor": "binary_sensor.fenetre_chambre", "my_button": ""}
        ]

    async def test_remove_shows_form_then_drops_the_cover(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_DAILY_COVER_ITEMS] = [{"cover": "cover.chambre", "window_sensor": ""}]
        form = await flow.async_step_cover_item_remove()
        assert form["step_id"] == "cover_item_remove"

        result = await flow.async_step_cover_item_remove({"remove_covers": ["cover.chambre"]})
        assert result["step_id"] == "cover_items"
        assert flow._data[CONF_DAILY_COVER_ITEMS] == []


class TestOptionsFlowCoverItemSteps:
    """The options flow exposes the same individual-cover steps, seeded from the entry."""

    async def test_menu_and_add_round_trip(self):
        flow = _make_options_flow({CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": ""}]})
        await flow.async_step_init()

        menu = await flow.async_step_cover_items()
        assert menu["menu_options"] == ["cover_item_add", "cover_item_remove", "menu"]

        result = await flow.async_step_cover_item_add(
            {"cover": "cover.b", "window_sensor": "binary_sensor.b"}
        )
        assert result["step_id"] == "cover_items"
        assert flow._data[CONF_DAILY_COVER_ITEMS] == [
            {"cover": "cover.a", "window_sensor": ""},
            {"cover": "cover.b", "window_sensor": "binary_sensor.b", "my_button": ""},
        ]

    async def test_remove_clears_the_list(self):
        flow = _make_options_flow({CONF_DAILY_COVER_ITEMS: [{"cover": "cover.a", "window_sensor": ""}]})
        await flow.async_step_init()
        result = await flow.async_step_cover_item_remove({"remove_covers": ["cover.a"]})
        assert result["step_id"] == "cover_items"
        assert flow._data[CONF_DAILY_COVER_ITEMS] == []
# ---------------------------------------------------------------------------
# Optional entity fields must not default to "" (an EntitySelector rejects it)
# ---------------------------------------------------------------------------

class TestEntityFieldsAreNeverEmptyByDefault:
    """An EntitySelector validates its value as an entity id, so a field left
    at default="" renders with "Entity is neither a valid entity ID nor a
    valid UUID" before the user has touched anything.
    """

    def _markers(self, schema) -> dict:
        return {marker.schema: marker for marker in schema.schema}

    def test_add_cover_optional_fields_have_no_default(self):
        markers = self._markers(cf._cover_item_add_schema())
        for key in ("window_sensor", "my_button"):
            assert markers[key].default is vol.UNDEFINED, key

    def test_cover_step_entity_fields_have_no_default_when_unset(self):
        markers = self._markers(cf._covers_schema(_make_hass(), {}))
        for key in ("cover_temp_sensor", "cover_my_button", "cover_weather_entity"):
            assert markers[key].default is vol.UNDEFINED, key

    def test_cover_step_entity_fields_suggest_the_stored_value(self):
        data = {
            "cover_temp_sensor": "sensor.temp",
            "cover_my_button": "button.my",
            "cover_weather_entity": "weather.home",
        }
        markers = self._markers(cf._covers_schema(_make_hass(), data))
        for key, value in data.items():
            assert markers[key].default is vol.UNDEFINED, key
            assert markers[key].description == {"suggested_value": value}, key

    def test_calendar_fields_have_no_default_on_first_setup(self):
        """The very first Calendars form must not open on two error boxes."""
        markers = self._markers(cf._calendars_schema({}))
        for key in (CONF_CALENDAR_ENTITY, CONF_HOLIDAY_CALENDAR):
            assert markers[key].default is vol.UNDEFINED, key
            assert isinstance(markers[key], vol.Required), key

    def test_calendar_fields_suggest_the_stored_value(self):
        data = {CONF_CALENDAR_ENTITY: "calendar.a", CONF_HOLIDAY_CALENDAR: "calendar.b"}
        markers = self._markers(cf._calendars_schema(data))
        assert markers[CONF_CALENDAR_ENTITY].description == {"suggested_value": "calendar.a"}
        assert markers[CONF_HOLIDAY_CALENDAR].description == {"suggested_value": "calendar.b"}


class TestClearingAnOptionalEntityField:
    """A cleared field is absent from the submitted data — it must not silently
    keep its previous value."""

    async def test_cleared_cover_entities_are_stored_as_empty(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data.update(
            {
                CONF_COVER_TEMP_SENSOR: "sensor.temp",
                "cover_my_button": "button.my",
                "cover_weather_entity": "weather.home",
            }
        )

        # the user cleared all three and submitted
        result = await flow.async_step_covers({CONF_COVER_ENTITIES: ["cover.salon"]})

        assert result["step_id"] == "menu"
        assert flow._data[CONF_COVER_TEMP_SENSOR] == ""
        assert flow._data["cover_my_button"] == ""
        assert flow._data["cover_weather_entity"] == ""
        assert flow._data[CONF_COVER_ENTITIES] == ["cover.salon"]

    async def test_submitted_values_still_win(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        await flow.async_step_covers({CONF_COVER_TEMP_SENSOR: "sensor.new"})
        assert flow._data[CONF_COVER_TEMP_SENSOR] == "sensor.new"

    async def test_add_cover_without_optional_fields_stores_empty_strings(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        await flow.async_step_cover_item_add({CONF_ITEM_COVER: "cover.chambre"})
        assert flow._data[CONF_DAILY_COVER_ITEMS] == [
            {"cover": "cover.chambre", "window_sensor": "", "my_button": ""}
        ]


class TestCloseTimePreview:
    """_close_time_preview: the two candidate closing times shown in the form."""

    def _hass(self, latitude=48.85, longitude=2.35):
        hass = _make_hass()
        hass.data = {}
        hass.config.latitude = latitude
        hass.config.longitude = longitude
        hass.config.time_zone = "Europe/Paris"
        hass.config.elevation = 0
        sun = MagicMock()
        sun.attributes = {"next_setting": "2026-07-01T19:30:00+00:00"}
        hass.states.get.side_effect = lambda eid: sun if eid == "sun.sun" else MagicMock()
        return hass

    def test_the_time_is_rendered_as_hh_mm(self):
        preview = cf._close_time_preview(self._hass(), {})
        assert re.fullmatch(r"\d{2}:\d{2}", preview["close_at_elevation"])

    def test_the_configured_elevation_is_echoed_back(self):
        """The form text names the value the time was computed from."""
        preview = cf._close_time_preview(
            self._hass(), {CONF_DAILY_COVER_CLOSE_ELEVATION: -2.5}
        )
        assert preview["close_elevation"] == "-2.5"

    def test_an_unreachable_elevation_renders_a_placeholder(self):
        """Polar summer: no time to show, but the form must still render."""
        hass = self._hass(latitude=78.2, longitude=15.6)
        with patch("custom_components.homeshift.config_flow.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 21, 12, 0, 0)
            preview = cf._close_time_preview(hass, {})
        assert preview["close_at_elevation"] == "--:--"

    def test_a_corrupted_setting_falls_back_to_the_default(self):
        preview = cf._close_time_preview(
            self._hass(), {CONF_DAILY_COVER_CLOSE_ELEVATION: "y"}
        )
        assert preview["close_elevation"] == f"{DEFAULT_DAILY_COVER_CLOSE_ELEVATION:g}"


class TestCloseElevationField:
    """The evening close is configured by one field and one field only."""

    def _marker(self, data):
        schema = cf._daily_cover_schema(_make_hass(), data)
        return next(m for m in schema.schema if m.schema == CONF_DAILY_COVER_CLOSE_ELEVATION)

    def test_the_retired_settings_are_gone_from_the_form(self):
        """The minute offset and the trigger choice no longer exist."""
        schema = cf._daily_cover_schema(_make_hass(), {CONF_DAY_MODE_MAP: DEFAULT_DAY_MODE_MAP})
        field_names = {marker.schema for marker in schema.schema}

        assert "daily_cover_close_offset_minutes" not in field_names
        assert "daily_cover_close_mode" not in field_names

    def test_it_defaults_to_the_recommended_value(self):
        assert self._marker({}).default() == DEFAULT_DAILY_COVER_CLOSE_ELEVATION

    def test_the_stored_value_is_preselected(self):
        assert self._marker({CONF_DAILY_COVER_CLOSE_ELEVATION: -4.5}).default() == -4.5

    def test_the_range_covers_every_retired_offset(self):
        """+-120 min around sunset spans roughly +21..-22° at mid latitude."""
        schema = cf._daily_cover_schema(_make_hass(), {})
        config = next(
            validator
            for marker, validator in schema.schema.items()
            if marker.schema == CONF_DAILY_COVER_CLOSE_ELEVATION
        ).config

        assert config["min"] == CLOSE_ELEVATION_MIN <= -22
        assert config["max"] == CLOSE_ELEVATION_MAX >= 21


class TestDailyCoverScheduleStepShowsThePreview:
    """Both flows hand the estimated closing times to the form description."""

    async def test_config_flow_passes_the_placeholders(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        result = await flow.async_step_daily_cover_schedule()
        assert set(result["description_placeholders"]) == {
            "close_elevation",
            "close_at_elevation",
        }

    async def test_options_flow_passes_the_placeholders(self):
        flow = _make_options_flow({CONF_DAY_MODE_MAP: "home:Home"})
        await flow.async_step_init()
        result = await flow.async_step_daily_cover_schedule()
        assert "close_at_elevation" in result["description_placeholders"]

    async def test_the_chosen_elevation_is_stored(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _make_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"
        await flow.async_step_daily_cover_schedule(
            {
                CONF_DAILY_COVER_CLOSE_ELEVATION: -3.5,
                "daily_open_time_home": "08:30",
            }
        )
        assert flow._data[CONF_DAILY_COVER_CLOSE_ELEVATION] == -3.5


def _located_hass(latitude: float, longitude: float, time_zone: str = "Europe/Paris") -> MagicMock:
    """A hass carrying a real location, for the astral-backed helpers."""
    hass = _make_hass()
    hass.data = {}
    hass.config.latitude = latitude
    hass.config.longitude = longitude
    hass.config.time_zone = time_zone
    hass.config.elevation = 0
    return hass


class TestValidateCloseElevation:
    """An elevation outside the sun's yearly range is caught in the form."""

    def _errors(self, hass, elevation):
        return cf._validate_close_elevation(
            hass, {CONF_DAILY_COVER_CLOSE_ELEVATION: elevation}
        )

    def test_every_offered_value_is_valid_at_mid_latitude(self):
        """At 43°N the sun sweeps the whole selector range every day of the year."""
        hass = _located_hass(43.45, 5.47)
        for elevation in (-18, -6, -2, 0, 2, 10):
            assert self._errors(hass, elevation) == {}, elevation

    def test_a_high_positive_value_is_rejected_further_north(self):
        """At 60°N the midwinter sun never climbs to 10°."""
        errors = self._errors(_located_hass(59.9, 10.75, "Europe/Oslo"), 10)

        assert errors == {CONF_DAILY_COVER_CLOSE_ELEVATION: "elevation_unreachable"}

    def test_the_polar_day_rejects_a_below_horizon_value(self):
        """Above the polar circle the June sun never sets at all."""
        errors = self._errors(_located_hass(78.2, 15.6, "Arctic/Longyearbyen"), -2)

        assert errors == {CONF_DAILY_COVER_CLOSE_ELEVATION: "elevation_unreachable"}

    def test_a_submission_without_the_field_is_not_validated(self):
        """Another step's input must not be judged on a value it never sent."""
        hass = _located_hass(78.2, 15.6, "Arctic/Longyearbyen")

        assert cf._validate_close_elevation(hass, {"daily_open_time_home": "sunrise"}) == {}


class TestDailyCoverScheduleStepRejectsAnUnreachableElevation:
    """Both flows surface the error on the field instead of storing the value."""

    def _polar_hass(self):
        return _located_hass(78.2, 15.6, "Arctic/Longyearbyen")

    def _input(self):
        return {
            CONF_DAILY_COVER_CLOSE_ELEVATION: -2.0,
            "daily_open_time_home": "sunrise",
        }

    async def test_the_form_comes_back_with_the_error(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = self._polar_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"

        result = await flow.async_step_daily_cover_schedule(self._input())

        assert result["step_id"] == "daily_cover_schedule"
        assert result["errors"] == {CONF_DAILY_COVER_CLOSE_ELEVATION: "elevation_unreachable"}

    async def test_nothing_is_stored(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = self._polar_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"

        await flow.async_step_daily_cover_schedule(self._input())

        assert CONF_DAILY_COVER_CLOSE_ELEVATION not in flow._data
        assert CONF_DAILY_COVER_OPEN_TIME_MAP not in flow._data

    async def test_the_rejected_form_still_shows_what_was_typed(self):
        """Re-rendering from the stored data would wipe the whole screen."""
        flow = cf.HomeShiftConfigFlow()
        flow.hass = self._polar_hass()
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"

        result = await flow.async_step_daily_cover_schedule(self._input())

        defaults = {
            marker.schema: marker.default()
            for marker in result["data_schema"].schema
            if marker.default is not vol.UNDEFINED
        }
        assert defaults[CONF_DAILY_COVER_CLOSE_ELEVATION] == -2.0
        assert defaults["daily_open_time_home"] == "sunrise"

    async def test_a_valid_elevation_goes_through(self):
        flow = cf.HomeShiftConfigFlow()
        flow.hass = _located_hass(43.45, 5.47)
        flow._data[CONF_DAY_MODE_MAP] = "home:Home"

        result = await flow.async_step_daily_cover_schedule(self._input())

        assert result["step_id"] == "menu"
        assert flow._data[CONF_DAILY_COVER_CLOSE_ELEVATION] == -2.0

    async def test_the_options_flow_validates_too(self):
        flow = _make_options_flow({CONF_DAY_MODE_MAP: "home:Home"})
        flow.hass = self._polar_hass()
        flow.hass.config_entries.async_get_known_entry.return_value = MagicMock(
            data={CONF_DAY_MODE_MAP: "home:Home"}, options={}
        )
        await flow.async_step_init()

        result = await flow.async_step_daily_cover_schedule(self._input())

        assert result["errors"] == {CONF_DAILY_COVER_CLOSE_ELEVATION: "elevation_unreachable"}
