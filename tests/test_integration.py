"""End-to-end tests on a real Home Assistant instance (pytest-homeassistant-custom-component).

The rest of the suite drives the coordinator against a MagicMock hass. These
tests set the integration up the way Home Assistant does — config entry,
platforms, entity and device registries, services — to cover what a mock
cannot: entity ids, translations, setup/unload and reloads.
"""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.homeshift.const import (
    CONF_CALENDAR_ENTITY,
    CONF_DAILY_COVER_ITEMS,
    CONF_HOLIDAY_CALENDAR,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

WORK_CALENDAR = "calendar.travail"
HOLIDAY_CALENDAR = "calendar.jours_feries"
COVER_ITEMS = [{"cover": "cover.salon", "window_sensor": "", "my_button": ""}]

# The entity ids dashboards, automations and the HomeShift card rely on.
EXPECTED_ENTITY_IDS = {
    "select.homeshift_day_mode",
    "select.homeshift_thermostat_mode",
    "number.homeshift_override_duration",
    "number.homeshift_early_switch",
    "sensor.homeshift_next_mode",
    "sensor.homeshift_next_mode_at",
    "sensor.homeshift_cover_open_time",
    "sensor.homeshift_cover_close_time",
    "binary_sensor.homeshift_covers_left_open",
}


def make_entry(data: dict | None = None, options: dict | None = None, version: int = 5) -> MockConfigEntry:
    """Return a HomeShift config entry wired to the two test calendars."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="HomeShift",
        version=version,
        data={CONF_CALENDAR_ENTITY: WORK_CALENDAR, CONF_HOLIDAY_CALENDAR: HOLIDAY_CALENDAR, **(data or {})},
        options=options or {},
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry, *, calendar_state: str = "off") -> None:
    """Add the entry, create the calendars it reads, and set it up."""
    hass.states.async_set(WORK_CALENDAR, calendar_state)
    hass.states.async_set(HOLIDAY_CALENDAR, "off")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def homeshift_entity_ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    """Return the entity ids registered for the entry."""
    return {e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)}


@pytest.mark.parametrize("language", ["en", "fr"])
async def test_entity_ids_do_not_depend_on_the_language(hass: HomeAssistant, language: str) -> None:
    """A French install gets the same entity ids as an English one (audit A1).

    Names come from the translations, so Home Assistant would otherwise
    derive select.homeshift_mode_jour on a French instance.
    """
    hass.config.language = language
    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})

    await setup_entry(hass, entry)

    assert EXPECTED_ENTITY_IDS <= homeshift_entity_ids(hass, entry)


async def test_names_follow_the_instance_language(hass: HomeAssistant) -> None:
    hass.config.language = "fr"
    entry = make_entry()

    await setup_entry(hass, entry)

    state = hass.states.get("select.homeshift_day_mode")
    assert state.attributes["friendly_name"] == "HomeShift Mode Jour"
    assert state.state == "Maison"


async def test_unconfigured_features_leave_no_stale_entity(hass: HomeAssistant) -> None:
    """Removing the covers from the options removes their entities (audit A5)."""
    entry = make_entry(
        options={
            CONF_DAILY_COVER_ITEMS: COVER_ITEMS,
            "cover_entities": ["cover.sud"],
            "cover_temp_sensor": "sensor.exterieur",
        }
    )
    await setup_entry(hass, entry)
    ids = homeshift_entity_ids(hass, entry)
    assert "sensor.homeshift_cover_open_time" in ids
    assert "binary_sensor.homeshift_cover_heat_active" in ids

    hass.config_entries.async_update_entry(entry, options={})
    await hass.async_block_till_done()

    ids = homeshift_entity_ids(hass, entry)
    assert "sensor.homeshift_cover_open_time" not in ids
    assert "sensor.homeshift_cover_close_time" not in ids
    assert "binary_sensor.homeshift_covers_left_open" not in ids
    assert "binary_sensor.homeshift_cover_heat_active" not in ids
    assert "select.homeshift_day_mode" in ids


async def test_removing_the_entry_deletes_its_stores(hass: HomeAssistant, hass_storage: dict) -> None:
    """No orphan .storage files once the integration is deleted (audit A4)."""
    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.homeshift_day_mode", "option": "Away"}, blocking=True
    )
    await hass.async_block_till_done()
    keys = [key for key in hass_storage if entry.entry_id in key]
    assert keys, "the coordinator should have persisted its state"

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert not [key for key in hass_storage if entry.entry_id in key]


async def test_diagnostics_report_the_configuration_and_the_state(hass: HomeAssistant) -> None:
    from custom_components.homeshift.diagnostics import async_get_config_entry_diagnostics

    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["version"] == 5
    assert diagnostics["entry"]["options"][CONF_DAILY_COVER_ITEMS] == COVER_ITEMS
    assert diagnostics["coordinator"]["data"]["day_mode_key"] in {"home", "work", "remote", "away"}
    assert "cover_open_time" in diagnostics["covers"]


async def test_entities_belong_to_one_service_device(hass: HomeAssistant) -> None:
    from homeassistant.helpers import device_registry as dr

    entry = make_entry()
    await setup_entry(hass, entry)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert devices[0].entry_type is dr.DeviceEntryType.SERVICE
    assert devices[0].name == "HomeShift"


# ---------------------------------------------------------------------------
# Setup, unload and reload
# ---------------------------------------------------------------------------


async def test_setup_and_unload(hass: HomeAssistant) -> None:
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.const import STATE_UNAVAILABLE

    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert hass.services.has_service(DOMAIN, "sync_calendar")
    assert hass.services.has_service(DOMAIN, "refresh_schedulers")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data
    assert not hass.services.has_service(DOMAIN, "sync_calendar")
    assert hass.states.get("select.homeshift_day_mode").state == STATE_UNAVAILABLE
    # No timer of the unloaded coordinator may fire later.
    assert coordinator._cancel_next_mode_timer is None
    assert coordinator._cancel_cover_open_timer is None
    assert coordinator._cancel_cover_close_timer is None


async def test_saving_options_reloads_the_entry(hass: HomeAssistant) -> None:
    from custom_components.homeshift.const import CONF_DAY_MODE_MAP

    entry = make_entry()
    await setup_entry(hass, entry)
    first = hass.data[DOMAIN][entry.entry_id]

    hass.config_entries.async_update_entry(
        entry, options={CONF_DAY_MODE_MAP: "home:House, work:Office, remote:Remote, away:Away"}
    )
    await hass.async_block_till_done()

    second = hass.data[DOMAIN][entry.entry_id]
    assert second is not first
    assert "Office" in hass.states.get("select.homeshift_day_mode").attributes["options"]


async def test_a_failing_first_refresh_leaves_no_timer_behind(hass: HomeAssistant) -> None:
    """ConfigEntryNotReady: the coordinator HA gives up on must not keep timers (audit P2)."""
    from unittest.mock import patch

    from homeassistant.config_entries import ConfigEntryState

    from custom_components.homeshift.coordinator import HomeShiftCoordinator

    built: list[HomeShiftCoordinator] = []
    original = HomeShiftCoordinator._schedule_cover_timers

    def _spy(self):
        built.append(self)
        original(self)

    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    with (
        patch.object(HomeShiftCoordinator, "_schedule_cover_timers", _spy),
        patch(
            "custom_components.homeshift.cover_manager.CoverManager.async_check_heat_protection",
            side_effect=RuntimeError("boom"),
        ),
    ):
        hass.states.async_set(WORK_CALENDAR, "off")
        hass.states.async_set(HOLIDAY_CALENDAR, "off")
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert built, "the first refresh should have armed the cover timers"
    for coordinator in built:
        assert coordinator._cancel_cover_open_timer is None
        assert coordinator._cancel_cover_close_timer is None
        assert coordinator._cancel_next_mode_timer is None


# ---------------------------------------------------------------------------
# Calendar outage (audit B2)
# ---------------------------------------------------------------------------


async def test_an_unavailable_calendar_keeps_the_mode(hass: HomeAssistant, freezer) -> None:
    """Remote day, then the calendar drops out: the mode stays on Remote."""
    freezer.move_to("2026-03-03 18:00:00+00:00")  # Tuesday, 10:00 in the test time zone
    entry = make_entry()
    hass.states.async_set(
        WORK_CALENDAR,
        "on",
        {"message": "Remote", "start_time": "2026-03-03 00:00:00", "end_time": "2026-03-04 00:00:00"},
    )
    hass.states.async_set(HOLIDAY_CALENDAR, "off")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("select.homeshift_day_mode").state == "Remote"

    hass.states.async_set(WORK_CALENDAR, "unavailable")
    await hass.services.async_call(DOMAIN, "sync_calendar", blocking=True)
    await hass.async_block_till_done()

    assert hass.states.get("select.homeshift_day_mode").state == "Remote"

    hass.states.async_set(WORK_CALENDAR, "off")
    await hass.services.async_call(DOMAIN, "sync_calendar", blocking=True)
    await hass.async_block_till_done()

    assert hass.states.get("select.homeshift_day_mode").state == "Work"


# ---------------------------------------------------------------------------
# Schedulers configured on a French instance (audit B1)
# ---------------------------------------------------------------------------


async def test_french_setup_without_the_mapping_step_drives_the_schedulers(hass: HomeAssistant, freezer) -> None:
    """Calendars, then Schedulers, then Save — the Mapping step never opened.

    The form used to offer Home/Work/... while the coordinator ran on
    Maison/Travail, so the work-day scheduler was never turned on.
    """
    from homeassistant.data_entry_flow import FlowResultType
    from pytest_homeassistant_custom_component.common import async_mock_service

    freezer.move_to("2026-03-03 18:00:00+00:00")  # Tuesday: a work day
    hass.config.language = "fr"
    hass.states.async_set(WORK_CALENDAR, "off")
    hass.states.async_set(HOLIDAY_CALENDAR, "off")
    hass.states.async_set("switch.schedule_bureau", "off")
    hass.states.async_set("switch.schedule_maison", "on")
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")

    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "calendars"})
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_CALENDAR_ENTITY: WORK_CALENDAR, CONF_HOLIDAY_CALENDAR: HOLIDAY_CALENDAR}
    )
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "schedulers"})
    fields = [str(marker) for marker in flow["data_schema"].schema]
    assert fields == ["schedulers_home", "schedulers_work", "schedulers_remote", "schedulers_away"]
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        {"schedulers_work": ["switch.schedule_bureau"], "schedulers_home": ["switch.schedule_maison"]},
    )
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "finalize"})
    assert flow["type"] is FlowResultType.CREATE_ENTRY
    assert flow["data"]["schedulers_per_mode"]["work"] == ["switch.schedule_bureau"]
    await hass.async_block_till_done()

    assert hass.states.get("select.homeshift_day_mode").state == "Travail"
    turned_on = [entity for call in turn_on for entity in call.data["entity_id"]]
    turned_off = [entity for call in turn_off for entity in call.data["entity_id"]]
    assert "switch.schedule_bureau" in turned_on
    assert "switch.schedule_maison" in turned_off
    assert "switch.schedule_bureau" not in turned_off


# ---------------------------------------------------------------------------
# Manual cover control: buttons and services
# ---------------------------------------------------------------------------


async def test_cover_buttons_exist_only_with_daily_covers(hass: HomeAssistant) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    ids = homeshift_entity_ids(hass, entry)
    assert "button.homeshift_open_covers" not in ids
    assert "button.homeshift_close_covers" not in ids

    hass.config_entries.async_update_entry(entry, options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await hass.async_block_till_done()
    ids = homeshift_entity_ids(hass, entry)
    assert {"button.homeshift_open_covers", "button.homeshift_close_covers"} <= ids

    hass.config_entries.async_update_entry(entry, options={})
    await hass.async_block_till_done()
    ids = homeshift_entity_ids(hass, entry)
    assert "button.homeshift_open_covers" not in ids


@pytest.mark.parametrize("language", ["en", "fr"])
async def test_cover_button_ids_and_names(hass: HomeAssistant, language: str) -> None:
    hass.config.language = language
    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)

    registry = er.async_get(hass)
    open_entry = registry.async_get("button.homeshift_open_covers")
    close_entry = registry.async_get("button.homeshift_close_covers")
    assert open_entry.unique_id == f"{entry.entry_id}_open_covers"
    assert close_entry.unique_id == f"{entry.entry_id}_close_covers"
    assert open_entry.translation_key == "open_covers"
    assert close_entry.translation_key == "close_covers"
    expected = {"en": "HomeShift Open covers", "fr": "HomeShift Ouvrir les volets"}[language]
    assert hass.states.get("button.homeshift_open_covers").attributes["friendly_name"] == expected
    assert hass.states.get("button.homeshift_open_covers").attributes["icon"] == "mdi:window-shutter-open"
    assert hass.states.get("button.homeshift_close_covers").attributes["icon"] == "mdi:window-shutter"


@pytest.mark.parametrize(
    ("press", "service"),
    [
        (("button", "press", {"entity_id": "button.homeshift_open_covers"}), "open_cover"),
        (("button", "press", {"entity_id": "button.homeshift_close_covers"}), "close_cover"),
        ((DOMAIN, "open_covers", {}), "open_cover"),
        ((DOMAIN, "close_covers", {}), "close_cover"),
    ],
)
async def test_buttons_and_services_move_the_covers(hass: HomeAssistant, freezer, press: tuple, service: str) -> None:
    from pytest_homeassistant_custom_component.common import async_mock_service

    freezer.move_to("2026-03-03 11:00:00+00:00")  # 03:00 local: no scheduled open or close due
    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)
    calls = async_mock_service(hass, "cover", service)

    domain, name, data = press
    await hass.services.async_call(domain, name, data, blocking=True)
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["entity_id"] == ["cover.salon"]


async def test_a_failing_cover_leaves_the_buttons_available(hass: HomeAssistant) -> None:
    """No cover service registered: the press is logged, nothing turns unavailable."""
    from homeassistant.const import STATE_UNAVAILABLE

    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)

    await hass.services.async_call("button", "press", {"entity_id": "button.homeshift_close_covers"}, blocking=True)
    await hass.async_block_till_done()

    assert hass.states.get("button.homeshift_close_covers").state != STATE_UNAVAILABLE
    assert hass.states.get("select.homeshift_day_mode").state != STATE_UNAVAILABLE


async def test_cover_services_are_removed_with_the_entry(hass: HomeAssistant) -> None:
    entry = make_entry(options={CONF_DAILY_COVER_ITEMS: COVER_ITEMS})
    await setup_entry(hass, entry)
    assert hass.services.has_service(DOMAIN, "open_covers")
    assert hass.services.has_service(DOMAIN, "close_covers")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "open_covers")
    assert not hass.services.has_service(DOMAIN, "close_covers")
