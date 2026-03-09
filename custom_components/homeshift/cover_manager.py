"""CoverManager – dedicated manager for cover heat-protection and sunrise scheduling.

Responsibilities
----------------
* **Heat protection**: When a temperature sensor exceeds a configured threshold
  *and* the current time is within the configured window, calls
  ``cover.stop_cover`` on the configured cover entities.  For Somfy covers
  ``stop_cover`` triggers the *my* preset which closes the cover to a
  pre-recorded, partially-closed position — it does **not** merely pause
  movement.

* **Sunrise scheduler adjustment**: Every morning at 00:15 reads
  ``sun.sun.next_rising`` and updates the start time of every configured
  scheduler-component switch to ``max(sunrise, earliest_time)``.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
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

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class CoverManager:
    """Manage cover heat-protection and sunrise-based scheduler adjustment.

    The coordinator owns a ``CoverManager`` instance and delegates all
    cover-related side-effects to it.  The manager itself is stateless:
    all configuration is read from *config_getter* on every call so that
    option-flow changes take effect immediately after a reload.

    Parameters
    ----------
    hass:
        The Home Assistant instance.
    config_getter:
        A zero-argument callable that returns the current merged config dict
        (``{**entry.data, **entry.options}``).  Using a callable rather than
        a snapshot dict ensures the manager always sees the latest config.
    """

    def __init__(self, hass: HomeAssistant, config_getter: Callable[[], dict]) -> None:
        """Initialise the manager."""
        self.hass = hass
        self._config_getter = config_getter

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _config(self) -> dict:
        """Return the current merged config dict."""
        return self._config_getter()

    # ------------------------------------------------------------------
    # Heat protection
    # ------------------------------------------------------------------

    async def async_heat_protection_check(self) -> None:
        """Close covers when temperature exceeds threshold during the configured window.

        This method is called whenever the configured temperature sensor
        changes state.  For Somfy covers, ``cover.stop_cover`` closes the
        cover to a pre-recorded *my* position — it does **not** simply pause
        movement.  The action is therefore only triggered once per temperature
        rise above the threshold; subsequent identical readings do nothing
        because the cover is already in the closed position.

        No-ops silently when:
        - No covers are configured.
        - No temperature sensor is configured.
        - The sensor state is unavailable or non-numeric.
        - The current time is outside the configured window.
        - The temperature is at or below the threshold.
        """
        covers: list[str] = self._config.get(CONF_HEAT_PROTECTION_COVERS, [])
        sensor: str = self._config.get(CONF_HEAT_PROTECTION_SENSOR, "")

        if not covers or not sensor:
            return

        try:
            threshold = float(
                self._config.get(CONF_HEAT_PROTECTION_THRESHOLD, DEFAULT_HEAT_PROTECTION_THRESHOLD)
            )
        except (ValueError, TypeError):
            threshold = DEFAULT_HEAT_PROTECTION_THRESHOLD

        start: str = self._config.get(CONF_HEAT_PROTECTION_START, DEFAULT_HEAT_PROTECTION_START)
        end: str = self._config.get(CONF_HEAT_PROTECTION_END, DEFAULT_HEAT_PROTECTION_END)

        now = dt_util.now()
        current_time = now.strftime("%H:%M:%S")

        if not (start <= current_time <= end):
            _LOGGER.debug(
                "Heat protection: outside time window (%s–%s), current=%s — no action",
                start,
                end,
                current_time,
            )
            return

        temp_state = self.hass.states.get(sensor)
        if not temp_state:
            _LOGGER.warning("Heat protection: temperature sensor '%s' not found", sensor)
            return

        try:
            temperature = float(temp_state.state)
        except (ValueError, TypeError):
            _LOGGER.debug(
                "Heat protection: sensor '%s' returned non-numeric state '%s' — no action",
                sensor,
                temp_state.state,
            )
            return

        if temperature > threshold:
            _LOGGER.info(
                "Heat protection: temp=%.1f°C > threshold=%.1f°C — closing covers %s",
                temperature,
                threshold,
                covers,
            )
            await self.hass.services.async_call(
                "cover",
                "stop_cover",
                {"entity_id": covers},
                blocking=False,
            )
        else:
            _LOGGER.debug(
                "Heat protection: temp=%.1f°C ≤ threshold=%.1f°C — no action",
                temperature,
                threshold,
            )

    # ------------------------------------------------------------------
    # Sunrise scheduler adjustment
    # ------------------------------------------------------------------

    async def async_adjust_sunrise_schedulers(self) -> None:
        """Adjust scheduler-component start times based on next sunrise.

        Called every morning at 00:15.  For each configured scheduler switch,
        updates the first timeslot start time to ``max(sunrise, earliest_time)``
        so that covers never open before the earliest allowed time even when
        sunrise is very early in summer.

        No-ops silently when:
        - No scheduler entities are configured.
        - ``sun.sun`` entity is unavailable.
        - ``sun.sun`` has no ``next_rising`` attribute.
        """
        scheduler_entities: list[str] = self._config.get(CONF_SUNRISE_SCHEDULERS, [])
        earliest: str = self._config.get(CONF_SUNRISE_EARLIEST_TIME, DEFAULT_SUNRISE_EARLIEST_TIME)

        if not scheduler_entities:
            _LOGGER.debug("Sunrise adjustment: no schedulers configured — skipping")
            return

        sun_state = self.hass.states.get("sun.sun")
        if not sun_state:
            _LOGGER.warning("Sunrise adjustment: sun.sun entity not found — skipping")
            return

        next_rising_raw = sun_state.attributes.get("next_rising")
        if not next_rising_raw:
            _LOGGER.warning(
                "Sunrise adjustment: sun.sun has no next_rising attribute — skipping"
            )
            return

        try:
            next_rising_dt = dt_util.as_local(dt_util.parse_datetime(str(next_rising_raw)))
            if next_rising_dt is None:
                raise ValueError("parse_datetime returned None")
            sunrise_time = next_rising_dt.strftime("%H:%M:%S")
        except (ValueError, AttributeError, TypeError) as err:
            _LOGGER.warning(
                "Sunrise adjustment: could not parse next_rising '%s': %s",
                next_rising_raw,
                err,
            )
            return

        # target = max(sunrise, earliest) — lexicographic comparison works for HH:MM:SS
        target_time = sunrise_time if sunrise_time > earliest else earliest
        _LOGGER.info(
            "Sunrise adjustment: sunrise=%s, earliest=%s → target=%s",
            sunrise_time,
            earliest,
            target_time,
        )

        for entity_id in scheduler_entities:
            sched_state = self.hass.states.get(entity_id)
            if not sched_state:
                _LOGGER.warning(
                    "Sunrise adjustment: scheduler '%s' not found — skipping",
                    entity_id,
                )
                continue

            try:
                actions: list = list(sched_state.attributes.get("actions", [{}]))
                entities: list = list(sched_state.attributes.get("entities", []))

                if not actions:
                    _LOGGER.warning(
                        "Sunrise adjustment: scheduler '%s' has no actions — skipping",
                        entity_id,
                    )
                    continue

                # Mirror user automation: merge entity_id back into the action dict
                current_action: dict = dict(actions[0])
                if entities:
                    current_action["entity_id"] = entities[0]

                await self.hass.services.async_call(
                    "scheduler",
                    "edit",
                    {
                        "entity_id": entity_id,
                        "timeslots": [{"start": target_time, "actions": [current_action]}],
                    },
                    blocking=False,
                )
                _LOGGER.info(
                    "Sunrise adjustment: updated '%s' → start=%s",
                    entity_id,
                    target_time,
                )
            except (AttributeError, KeyError, IndexError, TypeError) as err:
                _LOGGER.warning(
                    "Sunrise adjustment: failed to update '%s': %s",
                    entity_id,
                    err,
                )
