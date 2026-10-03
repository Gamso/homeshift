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
