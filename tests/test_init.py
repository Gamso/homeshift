"""Tests for async_setup_entry startup calendar sync behaviour."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState

from custom_components.homeshift import (
    async_migrate_entry,
    async_setup_entry,
    async_setup_services,
    async_unload_entry,
)
from custom_components.homeshift.const import (
    DOMAIN,
    SERVICE_REFRESH_SCHEDULERS,
    SERVICE_SYNC_CALENDAR,
)

from .conftest import make_mock_entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hass(state: CoreState = CoreState.running) -> MagicMock:
    """Return a lightweight mock hass suitable for testing async_setup_entry."""
    hass = MagicMock()
    hass.state = state
    hass.config.language = "fr"
    hass.data = {}
    # async_create_task: capture the coroutine passed to it
    hass.async_create_task = MagicMock()
    # bus.async_listen_once: return a callable "unsubscribe" stub
    hass.bus.async_listen_once = MagicMock(return_value=lambda: None)
    # config_entries helpers used inside async_setup_entry
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services.async_register = MagicMock()
    return hass


def _make_entry_with_options(base_entry: MagicMock | None = None) -> MagicMock:
    """Return a mock ConfigEntry with add_update_listener and async_on_unload."""
    entry = base_entry or make_mock_entry()
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    unloaders: list = []
    entry.async_on_unload = MagicMock(side_effect=lambda fn: unloaders.append(fn))
    entry._unloaders = unloaders
    return entry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTimersAreCancelledWhenTheFirstRefreshFails:
    """The timer cancellations are registered before the first refresh (audit P2)."""

    async def test_cancellations_registered_before_a_failing_first_refresh(self):
        from homeassistant.exceptions import ConfigEntryNotReady

        hass = _make_hass(state=CoreState.running)
        entry = _make_entry_with_options()

        with patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord:
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock(side_effect=ConfigEntryNotReady)
            MockCoord.return_value = coord

            try:
                await async_setup_entry(hass, entry)
            except ConfigEntryNotReady:
                pass
            else:
                raise AssertionError("the failing first refresh must propagate")

        assert coord.async_cancel_next_mode_timer in entry._unloaders
        assert coord.async_cancel_cover_timers in entry._unloaders


class TestStartupCalendarSync:
    """Verify that async_setup_entry schedules a post-startup calendar sync."""

    async def test_sync_scheduled_immediately_when_ha_already_running(self):
        """When HA state is running, async_create_task is called to sync calendar."""
        hass = _make_hass(state=CoreState.running)
        entry = _make_entry_with_options()

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            await async_setup_entry(hass, entry)

        # hass.async_create_task should have been called (for the immediate sync)
        hass.async_create_task.assert_called_once()

    async def test_event_listener_registered_when_ha_not_yet_running(self):
        """When HA is still starting, a listener is registered on EVENT_HOMEASSISTANT_STARTED."""
        hass = _make_hass(state=CoreState.starting)
        entry = _make_entry_with_options()

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            await async_setup_entry(hass, entry)

        # A listener should have been registered for EVENT_HOMEASSISTANT_STARTED
        hass.bus.async_listen_once.assert_called_once()
        assert hass.bus.async_listen_once.call_args[0][0] == EVENT_HOMEASSISTANT_STARTED
        # async_create_task should NOT have been called (not yet running)
        hass.async_create_task.assert_not_called()

    async def test_listener_unsubscribe_registered_as_unload_hook(self):
        """The EVENT_HOMEASSISTANT_STARTED listener is cancelled on unload (if not yet fired)."""
        hass = _make_hass(state=CoreState.starting)
        entry = _make_entry_with_options()
        unsub_mock = MagicMock()
        hass.bus.async_listen_once = MagicMock(return_value=unsub_mock)

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            await async_setup_entry(hass, entry)

        # Simulate unloading before the event fires — the guard should cancel the listener.
        for fn in entry._unloaders:
            fn()
        unsub_mock.assert_called_once()

    async def test_unload_after_listener_fires_is_safe(self):
        """Unloading after EVENT_HOMEASSISTANT_STARTED fired does NOT try to cancel again."""
        hass = _make_hass(state=CoreState.starting)
        entry = _make_entry_with_options()
        registered_callback = None
        unsub_mock = MagicMock()

        def capture_listen_once(event_name, cb):
            nonlocal registered_callback
            registered_callback = cb
            return unsub_mock

        hass.bus.async_listen_once = MagicMock(side_effect=capture_listen_once)

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            await async_setup_entry(hass, entry)

        # Fire the event — the callback clears the cancel reference synchronously.
        registered_callback(MagicMock())

        # Simulate a later unload (e.g., options save) — must NOT call unsub_mock
        # a second time (that would log "Unable to remove unknown job listener").
        for fn in entry._unloaders:
            fn()
        unsub_mock.assert_not_called()

    async def test_startup_callback_calls_sync_calendar(self):
        """When EVENT_HOMEASSISTANT_STARTED fires, async_create_task runs sync_calendar."""
        hass = _make_hass(state=CoreState.starting)
        entry = _make_entry_with_options()

        registered_callback = None

        def capture_listen_once(event_name, callback):
            nonlocal registered_callback
            registered_callback = callback
            return lambda: None  # unsubscribe stub

        hass.bus.async_listen_once = MagicMock(side_effect=capture_listen_once)

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            await async_setup_entry(hass, entry)

        assert registered_callback is not None
        # Simulate EVENT_HOMEASSISTANT_STARTED firing — callback is now a sync @callback.
        registered_callback(MagicMock())
        # async_sync_calendar() was called to obtain the coroutine for async_create_task.
        coord.async_sync_calendar.assert_called_once()
        hass.async_create_task.assert_called()
class _MigrationHarness:
    """Shared harness: migrations chain, so the fake entry must record writes.

    async_update_entry applies data/options/version to the entry the way HA
    does, otherwise a later step in the same run reads what the earlier one
    was supposed to have replaced.
    """

    def _hass(self, entry=None) -> MagicMock:
        hass = MagicMock()
        hass.config.latitude = 43.45
        hass.config.longitude = 5.47
        hass.config.time_zone = "Europe/Paris"
        hass.config.elevation = 0
        hass.data = {}

        def _update(target, **kwargs):
            for key in ("data", "options", "version"):
                if key in kwargs:
                    setattr(target, key, kwargs[key])
            return True

        hass.config_entries.async_update_entry = MagicMock(side_effect=_update)
        return hass

    def _entry(self, data: dict, options: dict, version: int = 2) -> MagicMock:
        entry = MagicMock()
        entry.version = version
        entry.data = data
        entry.options = options
        return entry

    async def _run(self, hass, entry) -> None:
        with patch("custom_components.homeshift.er"):
            await async_migrate_entry(hass, entry)

    def _writes(self, hass, version: int) -> dict:
        """Return the kwargs of the call that bumped the entry to `version`."""
        for call in hass.config_entries.async_update_entry.call_args_list:
            if call.kwargs.get("version") == version:
                return call.kwargs
        raise AssertionError(f"no migration wrote version {version}")


class TestMigrationToVersion3(_MigrationHarness):
    """v2 → v3 folds the flat "Daily Cover Entities" list into the per-cover list."""

    async def _migrate(self, hass, entry) -> dict:
        await self._run(hass, entry)
        return self._writes(hass, 3)

    async def test_entities_become_items(self):
        hass = self._hass()
        entry = self._entry({}, {"daily_cover_entities": ["cover.volets", "cover.bureau"]})

        updated = await self._migrate(hass, entry)

        assert updated["version"] == 3
        assert updated["options"]["daily_cover_items"] == [
            {"cover": "cover.volets", "window_sensor": "", "my_button": ""},
            {"cover": "cover.bureau", "window_sensor": "", "my_button": ""},
        ]
        assert "daily_cover_entities" not in updated["options"]
        assert "daily_cover_entities" not in updated["data"]

    async def test_existing_items_are_kept_first_and_not_duplicated(self):
        hass = self._hass()
        entry = self._entry(
            {},
            {
                "daily_cover_entities": ["cover.chambre", "cover.volets"],
                "daily_cover_items": [
                    {"cover": "cover.chambre", "window_sensor": "binary_sensor.f", "my_button": ""}
                ],
            },
        )

        updated = await self._migrate(hass, entry)

        assert updated["options"]["daily_cover_items"] == [
            {"cover": "cover.chambre", "window_sensor": "binary_sensor.f", "my_button": ""},
            {"cover": "cover.volets", "window_sensor": "", "my_button": ""},
        ]

    async def test_entities_stored_in_data_are_migrated_too(self):
        """An entry that was never edited through the options flow."""
        hass = self._hass()
        entry = self._entry({"daily_cover_entities": ["cover.volets"]}, {})

        updated = await self._migrate(hass, entry)

        assert updated["data"] == {}
        assert updated["options"]["daily_cover_items"] == [
            {"cover": "cover.volets", "window_sensor": "", "my_button": ""}
        ]

    async def test_other_keys_are_left_untouched(self):
        hass = self._hass()
        entry = self._entry(
            {"calendar_entity": "calendar.a"},
            {"daily_cover_entities": ["cover.volets"], "sunrise_earliest": "07:10:00"},
        )

        updated = await self._migrate(hass, entry)

        assert updated["data"]["calendar_entity"] == "calendar.a"
        assert updated["options"]["sunrise_earliest"] == "07:10:00"

    async def test_nothing_configured_leaves_an_empty_list(self):
        hass = self._hass()
        entry = self._entry({}, {})

        updated = await self._migrate(hass, entry)

        assert updated["version"] == 3
        assert "daily_cover_items" not in updated["options"]

    async def test_an_already_migrated_entry_skips_this_step(self):
        hass = self._hass()
        entry = self._entry({}, {"daily_cover_items": [{"cover": "cover.a"}]}, version=3)

        await self._run(hass, entry)

        versions = [
            call.kwargs.get("version")
            for call in hass.config_entries.async_update_entry.call_args_list
        ]
        assert 3 not in versions

class TestUnloadRemovesServices:
    """async_unload_entry drops the services once the last entry is gone.

    Services registered for good would keep showing up in Developer Tools and
    would act on an unloaded coordinator (writing to its store, calling
    cover/switch services).
    """

    def _hass_with_entries(self, *entry_ids: str) -> MagicMock:
        hass = MagicMock()
        hass.data = {DOMAIN: {entry_id: MagicMock() for entry_id in entry_ids}}
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.services.async_remove = MagicMock()
        return hass

    async def test_services_removed_with_the_last_entry(self):
        hass = self._hass_with_entries("entry_a")
        entry = make_mock_entry()
        entry.entry_id = "entry_a"

        result = await async_unload_entry(hass, entry)

        assert result is True
        removed = {call.args[1] for call in hass.services.async_remove.call_args_list}
        assert removed == {SERVICE_REFRESH_SCHEDULERS, SERVICE_SYNC_CALENDAR, "open_covers", "close_covers"}
        assert DOMAIN not in hass.data

    async def test_services_kept_while_another_entry_is_loaded(self):
        hass = self._hass_with_entries("entry_a", "entry_b")
        entry = make_mock_entry()
        entry.entry_id = "entry_a"

        await async_unload_entry(hass, entry)

        hass.services.async_remove.assert_not_called()
        assert list(hass.data[DOMAIN]) == ["entry_b"]

    async def test_nothing_removed_when_the_platforms_fail_to_unload(self):
        hass = self._hass_with_entries("entry_a")
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        entry = make_mock_entry()
        entry.entry_id = "entry_a"

        result = await async_unload_entry(hass, entry)

        assert result is False
        hass.services.async_remove.assert_not_called()
        assert list(hass.data[DOMAIN]) == ["entry_a"]


class TestServicesTargetTheLoadedCoordinator:
    """The handlers look the coordinator up at call time, not at registration."""

    def _register(self) -> tuple[MagicMock, dict]:
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        handlers: dict = {}
        hass.services.async_register = MagicMock(
            side_effect=lambda _domain, name, handler: handlers.__setitem__(name, handler)
        )
        async_setup_services(hass)
        return hass, handlers

    async def test_sync_calendar_hits_the_coordinator_loaded_afterwards(self):
        """A coordinator registered after the services still receives the call."""
        hass, handlers = self._register()
        coordinator = MagicMock()
        coordinator.async_sync_calendar = AsyncMock()
        hass.data[DOMAIN]["entry_a"] = coordinator

        await handlers[SERVICE_SYNC_CALENDAR](None)

        coordinator.async_sync_calendar.assert_awaited_once()

    async def test_refresh_schedulers_is_a_noop_once_unloaded(self):
        """No loaded entry: the call does nothing instead of touching a dead coordinator."""
        hass, handlers = self._register()
        stale = MagicMock()
        stale.async_refresh_schedulers = AsyncMock()
        hass.data[DOMAIN]["entry_a"] = stale
        hass.data[DOMAIN].clear()  # entry unloaded

        await handlers[SERVICE_REFRESH_SCHEDULERS](None)

        stale.async_refresh_schedulers.assert_not_called()


class TestMigrationToVersion4(_MigrationHarness):
    """v3 → v4 converts the retired sunset offset into the elevation it landed on.

    The reference location is Gardanne (43.45°N): sunset + 10 min sits at
    -2.5° there, sunset - 10 min at +1.5°, measured with astral.
    """

    async def _migrate(self, options: dict, data: dict | None = None) -> dict:
        hass = self._hass()
        entry = self._entry(data or {}, options, version=3)
        await self._run(hass, entry)
        return self._writes(hass, 4)

    def _covers(self) -> list[dict]:
        return [{"cover": "cover.volets", "window_sensor": "", "my_button": ""}]

    async def test_a_stored_offset_becomes_the_elevation_it_landed_on(self):
        """Closing 10 min before sunset is +1.5° at this latitude."""
        updated = await self._migrate(
            {"daily_cover_items": self._covers(), "daily_cover_close_offset_minutes": -10}
        )

        assert updated["version"] == 4
        assert updated["options"]["daily_cover_close_elevation"] == 1.5

    async def test_an_entry_that_never_touched_the_offset_gets_the_default_converted(self):
        """It was silently running on +10 min, which is -2.5° here."""
        updated = await self._migrate({"daily_cover_items": self._covers()})

        assert updated["options"]["daily_cover_close_elevation"] == -2.5

    async def test_the_retired_keys_are_stripped_from_data_and_options(self):
        updated = await self._migrate(
            {"daily_cover_items": self._covers(), "daily_cover_close_offset_minutes": 10},
            data={"daily_cover_close_offset_minutes": 30, "calendar_entity": "calendar.a"},
        )

        assert "daily_cover_close_offset_minutes" not in updated["options"]
        assert "daily_cover_close_offset_minutes" not in updated["data"]
        assert "daily_cover_close_mode" not in updated["options"]
        assert updated["data"]["calendar_entity"] == "calendar.a"

    async def test_an_entry_that_already_picked_an_elevation_keeps_it(self):
        """The intermediate build let the elevation be chosen explicitly."""
        updated = await self._migrate(
            {
                "daily_cover_items": self._covers(),
                "daily_cover_close_mode": "elevation",
                "daily_cover_close_elevation": -6.0,
                "daily_cover_close_offset_minutes": 10,
            }
        )

        assert updated["options"]["daily_cover_close_elevation"] == -6.0

    async def test_an_unused_daily_schedule_gets_no_setting(self):
        """No cover is driven, so there is nothing to convert."""
        updated = await self._migrate({"daily_cover_close_offset_minutes": 10})

        assert updated["version"] == 4
        assert "daily_cover_close_elevation" not in updated["options"]

    async def test_a_corrupted_offset_converts_the_default_instead(self):
        updated = await self._migrate(
            {"daily_cover_items": self._covers(), "daily_cover_close_offset_minutes": "nonsense"}
        )

        assert updated["options"]["daily_cover_close_elevation"] == -2.5

    async def test_an_unusable_location_falls_back_to_the_recommended_value(self):
        from custom_components.homeshift.const import DEFAULT_DAILY_COVER_CLOSE_ELEVATION

        hass = self._hass()
        entry = self._entry({}, {"daily_cover_items": self._covers()}, version=3)
        with patch("custom_components.homeshift.elevation_for_sunset_offset", return_value=None):
            await self._run(hass, entry)

        assert (
            self._writes(hass, 4)["options"]["daily_cover_close_elevation"]
            == DEFAULT_DAILY_COVER_CLOSE_ELEVATION
        )

    async def test_an_elevation_outside_the_offered_range_is_clamped(self, caplog):
        from custom_components.homeshift.const import CLOSE_ELEVATION_MAX

        hass = self._hass()
        entry = self._entry({}, {"daily_cover_items": self._covers()}, version=3)
        with patch("custom_components.homeshift.elevation_for_sunset_offset", return_value=40.0):
            with caplog.at_level("WARNING"):
                await self._run(hass, entry)

        assert self._writes(hass, 4)["options"]["daily_cover_close_elevation"] == CLOSE_ELEVATION_MAX
        assert "clamped" in caplog.text

    async def test_a_v2_entry_runs_both_migrations_in_one_go(self):
        """The old flat list and the old offset are both retired at once."""
        hass = self._hass()
        entry = self._entry({}, {"daily_cover_entities": ["cover.volets"]}, version=2)

        await self._run(hass, entry)

        assert self._writes(hass, 3)["options"]["daily_cover_items"] == [
            {"cover": "cover.volets", "window_sensor": "", "my_button": ""}
        ]
        assert self._writes(hass, 4)["options"]["daily_cover_close_elevation"] == -2.5

    async def test_an_already_migrated_entry_is_left_alone(self):
        hass = self._hass()
        entry = self._entry({}, {"daily_cover_items": self._covers()}, version=5)

        await self._run(hass, entry)

        hass.config_entries.async_update_entry.assert_not_called()


class TestMigrationToVersion5(_MigrationHarness):
    """v4 → v5 re-keys the schedulers from display labels to day mode keys."""

    async def _migrate(self, data: dict, options: dict, language: str = "fr") -> dict:
        hass = self._hass()
        hass.config.language = language
        entry = self._entry(data, options, version=4)
        await self._run(hass, entry)
        return self._writes(hass, 5)

    async def test_current_labels_become_keys(self):
        updated = await self._migrate(
            {"day_mode_map": "home:Maison, work:Travail, remote:Télétravail, away:Absence"},
            {"schedulers_per_mode": {"Maison": ["switch.a"], "Travail": ["switch.b"]}},
        )

        assert updated["version"] == 5
        assert updated["options"]["schedulers_per_mode"] == {"home": ["switch.a"], "work": ["switch.b"]}

    async def test_english_labels_stored_by_a_french_form_are_repaired(self):
        """The B1 scenario: the form stored "Work" while the coordinator ran on "Travail"."""
        updated = await self._migrate(
            {"schedulers_per_mode": {"Home": ["switch.a"], "Work": ["switch.b"], "Remote": [], "Away": []}},
            {},
        )

        assert updated["data"]["schedulers_per_mode"] == {
            "home": ["switch.a"],
            "work": ["switch.b"],
            "remote": [],
            "away": [],
        }

    async def test_a_renamed_mode_is_resolved_through_the_current_map(self):
        updated = await self._migrate(
            {"day_mode_map": "home:Maison, work:Bureau, remote:Télétravail, away:Absence"},
            {"schedulers_per_mode": {"Bureau": ["switch.b"]}},
        )

        assert updated["options"]["schedulers_per_mode"] == {"work": ["switch.b"]}

    async def test_labels_resolving_to_the_same_key_are_merged(self):
        updated = await self._migrate(
            {},
            {"schedulers_per_mode": {"Work": ["switch.a", "switch.b"], "Travail": ["switch.b", "switch.c"]}},
        )

        assert updated["options"]["schedulers_per_mode"] == {"work": ["switch.a", "switch.b", "switch.c"]}

    async def test_an_unknown_label_is_kept(self, caplog):
        with caplog.at_level("WARNING"):
            updated = await self._migrate({}, {"schedulers_per_mode": {"Vacances": ["switch.a"]}})

        assert updated["options"]["schedulers_per_mode"] == {"Vacances": ["switch.a"]}
        assert "match no day mode" in caplog.text

    async def test_an_entry_without_schedulers_only_bumps_the_version(self):
        updated = await self._migrate({"calendar_entity": "calendar.a"}, {})

        assert updated["data"] == {"calendar_entity": "calendar.a"}
        assert updated["options"] == {}
