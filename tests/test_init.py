"""Tests for async_setup_entry startup calendar sync behaviour."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState

from custom_components.homeshift import async_setup_entry
from custom_components.homeshift.const import DOMAIN

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

class TestStartupCalendarSync:
    """Verify that async_setup_entry schedules a post-startup calendar sync."""

    def test_sync_scheduled_immediately_when_ha_already_running(self):
        """When HA state is running, async_create_task is called to sync calendar."""
        hass = _make_hass(state=CoreState.running)
        entry = _make_entry_with_options()

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord._cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        # hass.async_create_task should have been called (for the immediate sync)
        hass.async_create_task.assert_called_once()

    def test_event_listener_registered_when_ha_not_yet_running(self):
        """When HA is still starting, a listener is registered on EVENT_HOMEASSISTANT_STARTED."""
        hass = _make_hass(state=CoreState.starting)
        entry = _make_entry_with_options()

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord._cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        # A listener should have been registered for EVENT_HOMEASSISTANT_STARTED
        hass.bus.async_listen_once.assert_called_once()
        assert hass.bus.async_listen_once.call_args[0][0] == EVENT_HOMEASSISTANT_STARTED
        # async_create_task should NOT have been called (not yet running)
        hass.async_create_task.assert_not_called()

    def test_listener_unsubscribe_registered_as_unload_hook(self):
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
            coord._cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        # Simulate unloading before the event fires — the guard should cancel the listener.
        for fn in entry._unloaders:
            fn()
        unsub_mock.assert_called_once()

    def test_unload_after_listener_fires_is_safe(self):
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
            coord._cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        # Fire the event — the callback clears the cancel reference synchronously.
        registered_callback(MagicMock())

        # Simulate a later unload (e.g., options save) — must NOT call unsub_mock
        # a second time (that would log "Unable to remove unknown job listener").
        for fn in entry._unloaders:
            fn()
        unsub_mock.assert_not_called()

    def test_startup_callback_calls_sync_calendar(self):
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
            coord._cover_manager.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        assert registered_callback is not None
        # Simulate EVENT_HOMEASSISTANT_STARTED firing — callback is now a sync @callback.
        registered_callback(MagicMock())
        # async_sync_calendar() was called to obtain the coroutine for async_create_task.
        coord.async_sync_calendar.assert_called_once()
        hass.async_create_task.assert_called()
