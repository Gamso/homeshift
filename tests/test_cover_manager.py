"""Tests for CoverManager – heat protection and sunrise scheduler adjustment."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.homeshift.const import (
    CONF_HEAT_PROTECTION_COVERS,
    CONF_HEAT_PROTECTION_SENSOR,
    CONF_HEAT_PROTECTION_THRESHOLD,
    CONF_HEAT_PROTECTION_START,
    CONF_HEAT_PROTECTION_END,
    CONF_SUNRISE_SCHEDULERS,
    CONF_SUNRISE_EARLIEST_TIME,
    DEFAULT_HEAT_PROTECTION_THRESHOLD,
    DEFAULT_HEAT_PROTECTION_START,
    DEFAULT_HEAT_PROTECTION_END,
    DEFAULT_SUNRISE_EARLIEST_TIME,
)
from custom_components.homeshift.cover_manager import CoverManager

from .conftest import make_mock_hass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cover_manager(config: dict) -> tuple[CoverManager, MagicMock]:
    """Create a CoverManager with the given config dict and return (manager, hass)."""
    hass = make_mock_hass()
    manager = CoverManager(hass, lambda: config)
    return manager, hass


def _temp_state(value: str) -> MagicMock:
    state = MagicMock()
    state.state = value
    return state


# ---------------------------------------------------------------------------
# Heat Protection
# ---------------------------------------------------------------------------

class TestHeatProtection:
    """Verify CoverManager.async_heat_protection_check() behaviour."""

    # ------------------------------------------------------------------
    # No-op cases
    # ------------------------------------------------------------------

    def test_no_action_when_no_covers_configured(self):
        """No service call when covers list is empty."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: [],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
        })
        asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())
        hass.services.async_call.assert_not_called()

    def test_no_action_when_no_sensor_configured(self):
        """No service call when temperature sensor is not set."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "",
        })
        asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())
        hass.services.async_call.assert_not_called()

    def test_no_action_outside_time_window(self):
        """No service call when current time is outside the configured window."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: "09:00:00",
            CONF_HEAT_PROTECTION_END: "18:00:00",
        })
        hass.states.get.return_value = _temp_state("35")

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 8, 0, 0)  # 08:00 — before window
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_not_called()

    def test_no_action_when_temperature_at_threshold(self):
        """No service call when temperature equals threshold (must be strictly greater)."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: DEFAULT_HEAT_PROTECTION_START,
            CONF_HEAT_PROTECTION_END: DEFAULT_HEAT_PROTECTION_END,
        })
        hass.states.get.return_value = _temp_state("30.0")

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_not_called()

    def test_no_action_when_temperature_below_threshold(self):
        """No service call when temperature is below the threshold."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: DEFAULT_HEAT_PROTECTION_START,
            CONF_HEAT_PROTECTION_END: DEFAULT_HEAT_PROTECTION_END,
        })
        hass.states.get.return_value = _temp_state("28.5")

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_not_called()

    def test_no_action_when_sensor_not_found(self):
        """No service call when the temperature sensor entity does not exist."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: DEFAULT_HEAT_PROTECTION_START,
            CONF_HEAT_PROTECTION_END: DEFAULT_HEAT_PROTECTION_END,
        })
        hass.states.get.return_value = None  # sensor not found

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_not_called()

    def test_no_action_when_sensor_state_non_numeric(self):
        """No service call when the sensor state cannot be parsed as a float."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: DEFAULT_HEAT_PROTECTION_START,
            CONF_HEAT_PROTECTION_END: DEFAULT_HEAT_PROTECTION_END,
        })
        hass.states.get.return_value = _temp_state("unavailable")

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_not_called()

    # ------------------------------------------------------------------
    # Action cases
    # ------------------------------------------------------------------

    def test_closes_covers_when_hot_and_in_window(self):
        """cover.stop_cover is called when temp > threshold inside the window."""
        covers = ["cover.volet_salon", "cover.volet_chambre"]
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: covers,
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: "08:35:00",
            CONF_HEAT_PROTECTION_END: "18:00:00",
        })
        hass.states.get.return_value = _temp_state("32.5")
        hass.services.async_call = AsyncMock()

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_called_once_with(
            "cover",
            "stop_cover",
            {"entity_id": covers},
            blocking=False,
        )

    def test_uses_default_threshold_when_not_configured(self):
        """Default threshold (30.0 °C) is used when CONF_HEAT_PROTECTION_THRESHOLD is absent."""
        manager, hass = _make_cover_manager({
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_START: DEFAULT_HEAT_PROTECTION_START,
            CONF_HEAT_PROTECTION_END: DEFAULT_HEAT_PROTECTION_END,
            # threshold deliberately omitted → uses DEFAULT_HEAT_PROTECTION_THRESHOLD = 30.0
        })
        hass.states.get.return_value = _temp_state("30.1")  # just above default
        hass.services.async_call = AsyncMock()

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        hass.services.async_call.assert_called_once()

    def test_config_getter_is_called_lazily(self):
        """The config_getter callable is invoked on every check (lazy, not snapshot)."""
        calls: list[dict] = []
        config: dict = {
            CONF_HEAT_PROTECTION_COVERS: ["cover.salon"],
            CONF_HEAT_PROTECTION_SENSOR: "sensor.temp",
            CONF_HEAT_PROTECTION_THRESHOLD: 30.0,
            CONF_HEAT_PROTECTION_START: DEFAULT_HEAT_PROTECTION_START,
            CONF_HEAT_PROTECTION_END: DEFAULT_HEAT_PROTECTION_END,
        }

        def _config_getter():
            calls.append(dict(config))
            return config

        hass = make_mock_hass()
        manager = CoverManager(hass, _config_getter)
        hass.states.get.return_value = _temp_state("28")  # below threshold, no action needed

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 1, 11, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_heat_protection_check())

        assert len(calls) >= 1, "config_getter was never called"


# ---------------------------------------------------------------------------
# Sunrise Scheduler Adjustment
# ---------------------------------------------------------------------------

class TestSunriseSchedulers:
    """Verify CoverManager.async_adjust_sunrise_schedulers() behaviour."""

    # ------------------------------------------------------------------
    # No-op cases
    # ------------------------------------------------------------------

    def test_no_action_when_no_schedulers_configured(self):
        """No service call when CONF_SUNRISE_SCHEDULERS is empty."""
        manager, hass = _make_cover_manager({CONF_SUNRISE_SCHEDULERS: []})
        asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())
        hass.services.async_call.assert_not_called()

    def test_no_action_when_sun_entity_missing(self):
        """No service call when sun.sun entity is not available."""
        manager, hass = _make_cover_manager({
            CONF_SUNRISE_SCHEDULERS: ["switch.schedule_volets"],
        })
        hass.states.get.return_value = None  # sun.sun not found

        asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())
        hass.services.async_call.assert_not_called()

    def test_no_action_when_next_rising_missing(self):
        """No service call when sun.sun has no next_rising attribute."""
        manager, hass = _make_cover_manager({
            CONF_SUNRISE_SCHEDULERS: ["switch.schedule_volets"],
        })
        sun_state = MagicMock()
        sun_state.attributes = {}  # no next_rising
        hass.states.get.return_value = sun_state

        asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())
        hass.services.async_call.assert_not_called()

    # ------------------------------------------------------------------
    # Time clamping logic
    # ------------------------------------------------------------------

    def _make_sunrise_setup(self, sunrise_local: str, earliest: str):
        """Return (manager, hass) configured for a sunrise scenario."""
        config = {
            CONF_SUNRISE_SCHEDULERS: ["switch.schedule_volets_travail"],
            CONF_SUNRISE_EARLIEST_TIME: earliest,
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        manager = CoverManager(hass, lambda: config)

        # sun.sun state
        sun_state = MagicMock()
        sun_state.attributes = {"next_rising": f"2026-07-01T{sunrise_local}+02:00"}

        # scheduler state
        sched_state = MagicMock()
        sched_state.attributes = {
            "actions": [{"action": "cover.open_cover"}],
            "entities": ["cover.volet_salon"],
        }

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                return sun_state
            return sched_state

        hass.states.get.side_effect = _get_state
        return manager, hass

    def test_uses_sunrise_when_after_earliest(self):
        """Target time is sunrise when sunrise > earliest."""
        manager, hass = self._make_sunrise_setup(sunrise_local="07:30:00", earliest="07:10:00")

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.parse_datetime.return_value = datetime(2026, 7, 1, 7, 30, 0)
            mock_dt.as_local.return_value = datetime(2026, 7, 1, 7, 30, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())

        hass.services.async_call.assert_called_once()
        call_data = hass.services.async_call.call_args[0][2]
        assert call_data["timeslots"][0]["start"] == "07:30:00"

    def test_uses_earliest_when_sunrise_before_earliest(self):
        """Target time is earliest when sunrise < earliest."""
        manager, hass = self._make_sunrise_setup(sunrise_local="06:50:00", earliest="07:10:00")

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.parse_datetime.return_value = datetime(2026, 7, 1, 6, 50, 0)
            mock_dt.as_local.return_value = datetime(2026, 7, 1, 6, 50, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())

        hass.services.async_call.assert_called_once()
        call_data = hass.services.async_call.call_args[0][2]
        assert call_data["timeslots"][0]["start"] == "07:10:00"

    def test_uses_default_earliest_when_not_configured(self):
        """Default earliest (07:10:00) is used when CONF_SUNRISE_EARLIEST_TIME is absent."""
        config = {
            CONF_SUNRISE_SCHEDULERS: ["switch.schedule_volets_travail"],
            # earliest deliberately omitted
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        manager = CoverManager(hass, lambda: config)

        sun_state = MagicMock()
        sun_state.attributes = {"next_rising": "2026-07-01T06:00:00+02:00"}
        sched_state = MagicMock()
        sched_state.attributes = {
            "actions": [{"action": "cover.open_cover"}],
            "entities": ["cover.volet_salon"],
        }

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                return sun_state
            return sched_state

        hass.states.get.side_effect = _get_state

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.parse_datetime.return_value = datetime(2026, 7, 1, 6, 0, 0)
            mock_dt.as_local.return_value = datetime(2026, 7, 1, 6, 0, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())

        # sunrise 06:00 < default earliest 07:10 → target = "07:10:00"
        call_data = hass.services.async_call.call_args[0][2]
        assert call_data["timeslots"][0]["start"] == DEFAULT_SUNRISE_EARLIEST_TIME

    def test_entity_id_merged_into_action(self):
        """Entity ID is merged from entities list into the action dict."""
        config = {
            CONF_SUNRISE_SCHEDULERS: ["switch.schedule_volets_travail"],
            CONF_SUNRISE_EARLIEST_TIME: "07:00:00",
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        manager = CoverManager(hass, lambda: config)

        sun_state = MagicMock()
        sun_state.attributes = {"next_rising": "2026-07-01T07:30:00+02:00"}
        sched_state = MagicMock()
        sched_state.attributes = {
            "actions": [{"action": "cover.open_cover"}],
            "entities": ["cover.volet_salon"],
        }

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                return sun_state
            return sched_state

        hass.states.get.side_effect = _get_state

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.parse_datetime.return_value = datetime(2026, 7, 1, 7, 30, 0)
            mock_dt.as_local.return_value = datetime(2026, 7, 1, 7, 30, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())

        call_data = hass.services.async_call.call_args[0][2]
        action = call_data["timeslots"][0]["actions"][0]
        assert action.get("entity_id") == "cover.volet_salon"

    def test_missing_scheduler_entity_is_skipped(self):
        """A configured scheduler entity that does not exist is skipped gracefully."""
        config = {
            CONF_SUNRISE_SCHEDULERS: ["switch.missing"],
            CONF_SUNRISE_EARLIEST_TIME: "07:10:00",
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        manager = CoverManager(hass, lambda: config)

        sun_state = MagicMock()
        sun_state.attributes = {"next_rising": "2026-07-01T07:30:00+02:00"}

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                return sun_state
            return None  # scheduler not found

        hass.states.get.side_effect = _get_state

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.parse_datetime.return_value = datetime(2026, 7, 1, 7, 30, 0)
            mock_dt.as_local.return_value = datetime(2026, 7, 1, 7, 30, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())

        hass.services.async_call.assert_not_called()

    def test_scheduler_edit_called_with_correct_entity_id(self):
        """The scheduler.edit call uses the entity_id of the scheduler switch."""
        config = {
            CONF_SUNRISE_SCHEDULERS: ["switch.schedule_ouverture_volets_travail"],
            CONF_SUNRISE_EARLIEST_TIME: "07:00:00",
        }
        hass = make_mock_hass()
        hass.services.async_call = AsyncMock()
        manager = CoverManager(hass, lambda: config)

        sun_state = MagicMock()
        sun_state.attributes = {"next_rising": "2026-07-01T07:30:00+02:00"}
        sched_state = MagicMock()
        sched_state.attributes = {
            "actions": [{"action": "cover.open_cover"}],
            "entities": ["cover.volet_salon"],
        }

        def _get_state(entity_id):
            if entity_id == "sun.sun":
                return sun_state
            return sched_state

        hass.states.get.side_effect = _get_state

        with patch("custom_components.homeshift.cover_manager.dt_util") as mock_dt:
            mock_dt.parse_datetime.return_value = datetime(2026, 7, 1, 7, 30, 0)
            mock_dt.as_local.return_value = datetime(2026, 7, 1, 7, 30, 0)
            asyncio.get_event_loop().run_until_complete(manager.async_adjust_sunrise_schedulers())

        hass.services.async_call.assert_called_once()
        domain, service, data = hass.services.async_call.call_args[0]
        assert domain == "scheduler"
        assert service == "edit"
        assert data["entity_id"] == "switch.schedule_ouverture_volets_travail"
