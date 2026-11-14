"""Tests for the climate auto start/stop: a setpoint threshold per thermostat mode."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeshift.auto_start_stop import (
    AutoStartStopManager,
    default_climate,
    heat_pump_name,
    parse_items,
)
from custom_components.homeshift.const import CONF_AUTO_START_STOP_ITEMS

SWITCH = "switch.salon_enable_auto_start_stop"
CLIMATE = "climate.salon"
SALON = {"switch": SWITCH, "setpoint_thresholds": {"heating": 19.0, "cooling": 24.0}}


def _switch(value: str, name: str = "Salon Enable auto start/stop") -> MagicMock:
    state = MagicMock()
    state.state = value
    state.name = name
    return state


def _climate(setpoint, state="heat") -> MagicMock:
    climate = MagicMock()
    climate.state = state
    climate.attributes = {"temperature": setpoint}
    return climate


def _manager(states: dict, items: list, mode="heating"):
    hass = MagicMock()
    hass.states.get.side_effect = states.get
    hass.services.async_call = AsyncMock()
    current = {"mode": mode}
    on_change = MagicMock()
    manager = AutoStartStopManager(hass, {CONF_AUTO_START_STOP_ITEMS: items}, lambda: current["mode"], on_change)
    return hass, manager, current, on_change


def _turned(hass, service: str) -> None:
    hass.services.async_call.assert_awaited_once_with("switch", service, {"entity_id": SWITCH}, blocking=True)


class TestParseItems:
    def test_the_climate_is_deduced_from_the_switch_id(self):
        assert default_climate(SWITCH) == CLIMATE
        assert default_climate("switch.something_else") is None

    def test_an_explicit_climate_wins(self):
        (pump,) = parse_items([{**SALON, "climate": "climate.other"}])
        assert pump.climate == "climate.other"

    def test_the_thresholds_are_read_by_mode(self):
        (pump,) = parse_items([{**SALON, "setpoint_thresholds": {"Heating": "19", "cooling": 24.5}}])
        assert (pump.switch, pump.climate) == (SWITCH, CLIMATE)
        assert pump.thresholds == {"heating": 19.0, "cooling": 24.5}

    def test_an_unreadable_threshold_is_dropped_but_the_others_kept(self):
        (pump,) = parse_items([{**SALON, "setpoint_thresholds": {"heating": "warm", "cooling": 24}}])
        assert pump.thresholds == {"cooling": 24.0}

    @pytest.mark.parametrize("thresholds", [None, {}, {"heating": None}, {"heating": "warm"}])
    def test_an_item_without_a_usable_threshold_is_skipped(self, thresholds):
        assert parse_items([{**SALON, "setpoint_thresholds": thresholds}]) == []

    def test_an_item_with_no_climate_to_read_is_skipped(self):
        assert parse_items([{**SALON, "switch": "switch.custom"}]) == []

    def test_malformed_items_are_skipped(self):
        assert parse_items([None, {"setpoint_thresholds": {"heating": 19}}, "x"]) == []

    def test_the_switch_name_loses_its_vtherm_suffix(self):
        assert heat_pump_name("Salon Enable auto start/stop") == "Salon"
        assert heat_pump_name("Enable auto start/stop") == "Enable auto start/stop"


class TestHeating:
    async def test_a_setpoint_at_the_threshold_keeps_the_climate_running(self):
        hass, manager, *_ = _manager({SWITCH: _switch("on"), CLIMATE: _climate(19.0)}, [SALON])
        await manager.async_apply()
        _turned(hass, "turn_off")

    async def test_a_setpoint_below_it_lets_the_thermostat_stop_the_climate(self):
        hass, manager, *_ = _manager({SWITCH: _switch("off"), CLIMATE: _climate(17.5)}, [SALON])
        await manager.async_apply()
        _turned(hass, "turn_on")


class TestCooling:
    async def test_a_setpoint_at_the_threshold_keeps_the_climate_running(self):
        hass, manager, *_ = _manager({SWITCH: _switch("on"), CLIMATE: _climate(24.0)}, [SALON], mode="cooling")
        await manager.async_apply()
        _turned(hass, "turn_off")

    async def test_a_setpoint_above_it_lets_the_thermostat_stop_the_climate(self):
        hass, manager, *_ = _manager({SWITCH: _switch("off"), CLIMATE: _climate(28.0)}, [SALON], mode="cooling")
        await manager.async_apply()
        _turned(hass, "turn_on")

    async def test_each_mode_uses_its_own_threshold(self):
        states = {SWITCH: _switch("on"), CLIMATE: _climate(21.0)}
        heating, manager_heating, *_ = _manager(states, [SALON], mode="heating")
        cooling, manager_cooling, *_ = _manager(states, [SALON], mode="cooling")
        await manager_heating.async_apply()
        await manager_cooling.async_apply()
        _turned(heating, "turn_off")  # 21 >= 19
        _turned(cooling, "turn_off")  # 21 <= 24


class TestApply:
    async def test_the_threshold_is_read_again_at_each_change(self):
        states = {SWITCH: _switch("off"), CLIMATE: _climate(17.5)}
        hass, manager, *_ = _manager(states, [SALON])
        await manager.async_apply()
        hass.services.async_call.reset_mock()
        states[CLIMATE] = _climate(21.0)
        states[SWITCH] = _switch("on")

        await manager.async_apply()

        _turned(hass, "turn_off")

    async def test_a_switch_already_right_is_not_written(self):
        hass, manager, *_ = _manager({SWITCH: _switch("off"), CLIMATE: _climate(21.0)}, [SALON])
        await manager.async_apply()
        hass.services.async_call.assert_not_awaited()

    async def test_a_flip_by_hand_holds_until_the_next_transition(self):
        states = {SWITCH: _switch("off"), CLIMATE: _climate(21.0)}
        hass, manager, *_ = _manager(states, [SALON])
        await manager.async_apply()
        states[SWITCH] = _switch("on")  # flipped by hand

        await manager.async_apply()

        hass.services.async_call.assert_not_awaited()

    async def test_a_mode_change_writes_even_an_unchanged_state(self):
        states = {SWITCH: _switch("off"), CLIMATE: _climate(21.0)}
        hass, manager, *_ = _manager(states, [SALON])
        await manager.async_apply()
        states[SWITCH] = _switch("on")

        await manager.async_apply(force=True)

        _turned(hass, "turn_off")

    async def test_a_mode_without_a_threshold_leaves_the_switch_alone(self):
        states = {SWITCH: _switch("on"), CLIMATE: _climate(21.0)}
        hass, manager, *_ = _manager(states, [SALON], mode="ventilation")
        await manager.async_apply(force=True)
        hass.services.async_call.assert_not_awaited()

    async def test_entering_a_driven_mode_writes_the_switch(self):
        states = {SWITCH: _switch("on"), CLIMATE: _climate(21.0)}
        hass, manager, current, _ = _manager(states, [SALON], mode="ventilation")
        await manager.async_apply()
        current["mode"] = "heating"
        states[SWITCH] = _switch("on")

        await manager.async_apply(force=True)

        _turned(hass, "turn_off")

    @pytest.mark.parametrize("climate", [None, _climate(None), _climate(21.0, "unavailable")])
    async def test_without_a_setpoint_the_switch_is_left_alone(self, climate):
        states = {SWITCH: _switch("on")}
        if climate is not None:
            states[CLIMATE] = climate
        hass, manager, *_ = _manager(states, [SALON])
        await manager.async_apply()
        hass.services.async_call.assert_not_awaited()

    async def test_an_unavailable_switch_is_skipped(self):
        hass, manager, *_ = _manager({SWITCH: _switch("unavailable"), CLIMATE: _climate(21.0)}, [SALON])
        await manager.async_apply()
        hass.services.async_call.assert_not_awaited()

    async def test_a_switch_unavailable_at_first_is_written_once_it_appears(self):
        """Versatile Thermostat loads after HomeShift: the switch is set at the next run."""
        states = {SWITCH: _switch("unavailable"), CLIMATE: _climate(17.0)}
        hass, manager, *_ = _manager(states, [SALON])
        await manager.async_apply()
        hass.services.async_call.assert_not_awaited()

        states[SWITCH] = _switch("off")
        await manager.async_apply()
        _turned(hass, "turn_on")

    async def test_a_failed_write_is_tried_again(self):
        from homeassistant.exceptions import HomeAssistantError

        hass, manager, *_ = _manager({SWITCH: _switch("off"), CLIMATE: _climate(17.0)}, [SALON])
        hass.services.async_call.side_effect = HomeAssistantError("unreachable")
        await manager.async_apply()
        hass.services.async_call.side_effect = None
        hass.services.async_call.reset_mock()

        await manager.async_apply()
        _turned(hass, "turn_on")

    async def test_without_items_nothing_happens(self):
        hass, manager, *_ = _manager({}, [])
        await manager.async_apply()
        hass.services.async_call.assert_not_awaited()
        assert manager.configured is False

    async def test_a_setpoint_change_is_applied_and_shown(self):
        states = {SWITCH: _switch("off"), CLIMATE: _climate(21.0)}
        hass, manager, _, on_change = _manager(states, [SALON])
        await manager.async_apply()
        states[CLIMATE] = _climate(17.0)

        await manager.async_on_setpoint_change()

        _turned(hass, "turn_on")
        on_change.assert_called_once()


class TestStatus:
    def test_describes_each_climate(self):
        _, manager, *_ = _manager({SWITCH: _switch("on"), CLIMATE: _climate(21.0)}, [SALON])
        (status,) = manager.status()
        assert status == {
            "switch": SWITCH,
            "name": "Salon",
            "driven": True,
            "comfort": True,
            "auto_start_stop": True,
            "manual": True,
            "setpoint": 21.0,
            "threshold": 19.0,
            "comfort_when": "above",
        }

    def test_below_the_heating_threshold_it_is_not_in_comfort(self):
        _, manager, *_ = _manager({SWITCH: _switch("on"), CLIMATE: _climate(17.5)}, [SALON])
        (status,) = manager.status()
        assert status["comfort"] is False and status["manual"] is False

    def test_cooling_is_in_comfort_below_its_threshold(self):
        _, manager, *_ = _manager({SWITCH: _switch("off"), CLIMATE: _climate(23.0)}, [SALON], mode="cooling")
        (status,) = manager.status()
        assert (status["comfort"], status["threshold"], status["comfort_when"]) == (True, 24.0, "below")

    def test_a_mode_without_a_threshold_is_not_driven(self):
        _, manager, *_ = _manager({SWITCH: _switch("off"), CLIMATE: _climate(21.0)}, [SALON], mode="ventilation")
        (status,) = manager.status()
        assert status["driven"] is False
        assert status["comfort"] is None
        assert status["manual"] is False
        assert (status["threshold"], status["comfort_when"]) == (None, None)

    def test_the_switches_and_climates_to_follow_are_listed(self):
        _, manager, *_ = _manager({}, [SALON])
        assert manager.switches == [SWITCH]
        assert manager.climates == [CLIMATE]
