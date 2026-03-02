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
        """The EVENT_HOMEASSISTANT_STARTED listener unsubscribe is added to unload hooks."""
        hass = _make_hass(state=CoreState.starting)
        entry = _make_entry_with_options()
        unsub_sentinel = object()
        hass.bus.async_listen_once = MagicMock(return_value=unsub_sentinel)

        with (
            patch("custom_components.homeshift.HomeShiftCoordinator") as MockCoord,
        ):
            coord = MagicMock()
            coord.async_restore_state = AsyncMock()
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        # The unsubscribe callable should have been passed to entry.async_on_unload
        unloaders = entry._unloaders
        assert unsub_sentinel in unloaders

    def test_startup_callback_calls_sync_calendar(self):
        """When EVENT_HOMEASSISTANT_STARTED fires, async_sync_calendar is awaited."""
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
            coord.async_config_entry_first_refresh = AsyncMock()
            coord.async_sync_calendar = AsyncMock()
            MockCoord.return_value = coord

            asyncio.get_event_loop().run_until_complete(
                async_setup_entry(hass, entry)
            )

        assert registered_callback is not None
        # Simulate EVENT_HOMEASSISTANT_STARTED firing
        asyncio.get_event_loop().run_until_complete(registered_callback(MagicMock()))
        coord.async_sync_calendar.assert_awaited_once()
