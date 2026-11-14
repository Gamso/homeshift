"""Auto start/stop of climates, driven by the climate's setpoint.

Versatile Thermostat (over_climate) can stop a climate that has nothing to
do and restart it when needed; its switch.<vtherm>_enable_auto_start_stop
turns that on or off. Each thermostat mode has its own threshold. HomeShift
turns the switch off while the climate's target temperature is on the comfort
side of it (at or above in heating, at or below in cooling and ventilation),
so the climate keeps running, and on the other side: the scheduler's comfort
and eco slots (or presets) move the setpoint, and the auto start/stop follows.

It acts on transitions only — a thermostat mode change, a setpoint crossing
its threshold, the start of Home Assistant — never in between: a switch
flipped by hand stays as it is until the next transition.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_AUTO_START_STOP_ITEMS,
    CONF_ITEM_CLIMATE,
    CONF_ITEM_SETPOINT_THRESHOLDS,
    CONF_ITEM_SWITCH,
)

_LOGGER = logging.getLogger(__name__)


# Which side of its threshold the setpoint keeps the climate running, by
# thermostat mode: a heating setpoint at or above it (a comfort slot is warmer
# than an eco one), a cooling or ventilation setpoint at or below it (a comfort
# slot is cooler than an eco one).
COMFORT_ABOVE = "above"
COMFORT_BELOW = "below"
COMFORT_SIDE = {"heating": COMFORT_ABOVE, "cooling": COMFORT_BELOW, "ventilation": COMFORT_BELOW}


@dataclass
class HeatPump:
    """One switch driven by HomeShift: the climate that decides and a threshold per thermostat mode."""

    switch: str
    climate: str
    # Threshold in degrees by thermostat mode key; a mode without one is not driven.
    thresholds: dict[str, float]


def default_climate(switch: str) -> str | None:
    """Return the climate of a Versatile Thermostat switch, from its id.

    switch.salon_enable_auto_start_stop -> climate.salon, None for any other id.
    """
    match = re.fullmatch(r"switch\.(.+)_enable_auto_start_stop", switch)
    return f"climate.{match.group(1)}" if match else None


def heat_pump_name(name: str) -> str:
    """Drop the " Enable auto start/stop" Versatile Thermostat appends to the switch name."""
    return re.sub(r"\s*enable auto start/?stop$", "", name, flags=re.IGNORECASE) or name


def parse_items(raw: Any) -> list[HeatPump]:
    """Read the configured items, skipping those without a usable threshold or climate."""
    heat_pumps: list[HeatPump] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get(CONF_ITEM_SWITCH):
            continue
        switch = item[CONF_ITEM_SWITCH]
        thresholds: dict[str, float] = {}
        for mode, value in (item.get(CONF_ITEM_SETPOINT_THRESHOLDS) or {}).items():
            try:
                thresholds[str(mode).lower()] = float(value)
            except (TypeError, ValueError):
                _LOGGER.warning("Auto start/stop: ignoring the threshold '%s' of %s for '%s'", value, switch, mode)
        if not thresholds:
            _LOGGER.warning("Auto start/stop: ignoring %s, it has no setpoint threshold", switch)
            continue
        climate = item.get(CONF_ITEM_CLIMATE) or default_climate(switch)
        if not climate:
            _LOGGER.warning("Auto start/stop: ignoring %s, no climate to read the setpoint from", switch)
            continue
        heat_pumps.append(HeatPump(switch=switch, climate=climate, thresholds=thresholds))
    return heat_pumps


class AutoStartStopManager:
    """Turns the auto start/stop switches on and off at each transition."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        thermostat_mode: Callable[[], str | None],
        on_change: Callable[[], None],
    ) -> None:
        """Read the items; `thermostat_mode` returns the current thermostat mode key."""
        self._hass = hass
        self._heat_pumps = parse_items(config.get(CONF_AUTO_START_STOP_ITEMS))
        self._thermostat_mode = thermostat_mode
        self._on_change = on_change
        # What each switch was last set to (True: auto start/stop on), None
        # while it is not driven. A switch is only written again once this
        # changes, so a flip by hand holds until the next transition.
        self._applied: dict[str, bool | None] = {}
        self._started = False

    @property
    def configured(self) -> bool:
        """Return whether at least one switch is driven."""
        return bool(self._heat_pumps)

    @property
    def switches(self) -> list[str]:
        """Return the driven switches."""
        return [heat_pump.switch for heat_pump in self._heat_pumps]

    @property
    def climates(self) -> list[str]:
        """Return the climates whose setpoint decides, to follow their changes."""
        return [heat_pump.climate for heat_pump in self._heat_pumps]

    def _setpoint(self, heat_pump: HeatPump) -> float | None:
        """Return the target temperature of the climate, None when it has none right now."""
        state = self._hass.states.get(heat_pump.climate)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(state.attributes.get("temperature"))
        except (TypeError, ValueError):
            return None

    def _wanted(self, heat_pump: HeatPump, thermostat_key: str | None) -> bool | None:
        """Return the state the switch should have (True: on), None when not driven.

        A climate with no setpoint at the moment (off, unavailable, a preset
        without temperature) is left as it is.
        """
        mode = (thermostat_key or "").lower()
        threshold = heat_pump.thresholds.get(mode)
        setpoint = self._setpoint(heat_pump)
        if threshold is None or setpoint is None:
            return None
        if COMFORT_SIDE.get(mode, COMFORT_ABOVE) == COMFORT_ABOVE:
            return setpoint < threshold
        return setpoint > threshold

    def status(self) -> list[dict[str, Any]]:
        """Describe each climate for the sensor and the card."""
        thermostat_key = self._thermostat_mode()
        mode = (thermostat_key or "").lower()
        result: list[dict[str, Any]] = []
        for heat_pump in self._heat_pumps:
            wanted = self._wanted(heat_pump, thermostat_key)
            state = self._hass.states.get(heat_pump.switch)
            actual = None
            if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                actual = state.state == STATE_ON
            result.append(
                {
                    "switch": heat_pump.switch,
                    "name": self._name(heat_pump.switch, state),
                    "driven": wanted is not None,
                    "comfort": None if wanted is None else not wanted,
                    "auto_start_stop": actual,
                    "manual": wanted is not None and actual is not None and actual != wanted,
                    "setpoint": self._setpoint(heat_pump),
                    "threshold": heat_pump.thresholds.get(mode),
                    "comfort_when": COMFORT_SIDE.get(mode, COMFORT_ABOVE) if mode in heat_pump.thresholds else None,
                }
            )
        return result

    @staticmethod
    def _name(switch: str, state: Any) -> str:
        """Name of the climate: the switch's device name, else its friendly name."""
        name = getattr(state, "name", None) if state is not None else None
        return heat_pump_name(name if isinstance(name, str) and name else switch)

    async def async_apply(self, *, force: bool = False) -> None:
        """Set each driven switch to what the thermostat mode and setpoint want.

        `force` writes even the switches whose wanted state did not change
        (a thermostat mode change, the start of Home Assistant); otherwise only
        those whose wanted state changed are written.
        """
        if not self._heat_pumps:
            return
        force = force or not self._started
        self._started = True
        thermostat_key = self._thermostat_mode()
        for heat_pump in self._heat_pumps:
            wanted = self._wanted(heat_pump, thermostat_key)
            previous = self._applied.get(heat_pump.switch)
            if wanted is None:
                self._applied[heat_pump.switch] = None
                continue
            if wanted == previous and not force:
                continue
            # Only remembered once written: a switch not there yet (Versatile
            # Thermostat still loading) or a failed call is tried again at
            # the next run instead of waiting for the next transition.
            if await self._async_set(heat_pump.switch, wanted):
                self._applied[heat_pump.switch] = wanted

    async def _async_set(self, switch: str, on: bool) -> bool:
        """Turn a switch on or off, unless it is already there or cannot be reached.

        Returns whether the switch is now in the wanted state.
        """
        state = self._hass.states.get(switch)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("Auto start/stop: %s unavailable, left as it is", switch)
            return False
        if (state.state == STATE_ON) == on:
            return True
        _LOGGER.info("Auto start/stop: %s -> %s", switch, "on" if on else "off (comfort)")
        try:
            await self._hass.services.async_call(
                "switch", "turn_on" if on else "turn_off", {"entity_id": switch}, blocking=True
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Auto start/stop: could not turn %s %s: %s", switch, "on" if on else "off", err)
            return False
        return True

    async def async_on_setpoint_change(self) -> None:
        """Apply a setpoint that crossed its threshold, and show it."""
        await self.async_apply()
        self._on_change()
