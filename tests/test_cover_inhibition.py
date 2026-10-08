"""Tests for the manual inhibition of covers (inhibit_covers / resume_covers)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.homeshift import _inhibition_end
from custom_components.homeshift.const import (
    ATTR_DURATION,
    ATTR_UNTIL,
    CONF_COVER_ENTITIES,
    CONF_COVER_MY_BUTTON,
    CONF_COVER_TEMP_SENSOR,
    CONF_COVER_TEMP_THRESHOLD,
    CONF_DAILY_COVER_ITEMS,
)
from custom_components.homeshift.coordinator import HomeShiftCoordinator

from .conftest import make_mock_entry, make_mock_hass

TZ = UTC
NOW = datetime(2026, 7, 1, 12, 0, tzinfo=TZ)


def _items(*covers: str, window: dict | None = None, button: dict | None = None) -> list[dict]:
    return [
        {
            "cover": cover,
            "window_sensor": (window or {}).get(cover, ""),
            "my_button": (button or {}).get(cover, ""),
        }
        for cover in covers
    ]


def _coordinator(options: dict) -> tuple[MagicMock, HomeShiftCoordinator]:
    hass = make_mock_hass()
    hass.services.async_call = AsyncMock()
    entry = make_mock_entry()
    entry.options = options
    coordinator = HomeShiftCoordinator(hass, entry)
    manager = coordinator.cover_manager
    manager._store = MagicMock()
    manager._store.async_save = AsyncMock()
    manager.cover_open_time = "08:30"
    manager.daily_close_time = "21:40"
    return hass, coordinator


def _calls(hass: MagicMock) -> list[tuple]:
    return [(c.args[0], c.args[1], c.args[2]["entity_id"]) for c in hass.services.async_call.call_args_list]


class TestInhibitionState:
    """The inhibition bookkeeping itself."""

    async def test_inhibit_with_end_then_expires(self):
        _, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        manager = coordinator.cover_manager
        until = NOW + timedelta(days=3)

        await manager.async_inhibit(["cover.a"], until)

        assert manager.inhibitions(NOW) == {"cover.a": until}
        assert manager.is_inhibited("cover.a", NOW)
        assert not manager.is_inhibited("cover.b", NOW)
        assert manager.inhibitions(until) == {}

    async def test_inhibit_without_end_lasts_until_resumed(self):
        _, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a")})
        manager = coordinator.cover_manager

        await manager.async_inhibit(["cover.a"], None)
        assert manager.is_inhibited("cover.a", NOW + timedelta(days=365))

        await manager.async_resume(["cover.a"])
        assert manager.inhibitions(NOW) == {}

    async def test_inhibit_again_replaces_the_end(self):
        _, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a")})
        manager = coordinator.cover_manager

        await manager.async_inhibit(["cover.a"], None)
        await manager.async_inhibit(["cover.a"], NOW + timedelta(hours=1))

        assert manager.inhibitions(NOW) == {"cover.a": NOW + timedelta(hours=1)}

    async def test_resume_all(self):
        _, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        manager = coordinator.cover_manager
        await manager.async_inhibit(["cover.a", "cover.b"], None)

        await manager.async_resume()

        assert manager.inhibitions(NOW) == {}

    async def test_prune_drops_only_expired(self):
        _, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        manager = coordinator.cover_manager
        await manager.async_inhibit(["cover.a"], NOW - timedelta(minutes=1))
        await manager.async_inhibit(["cover.b"], None)
        manager._store.async_save.reset_mock()

        assert await manager.async_prune_inhibitions(NOW) is True
        assert manager._inhibited == {"cover.b": None}
        manager._store.async_save.assert_awaited_once()
        assert await manager.async_prune_inhibitions(NOW) is False

    async def test_persisted_and_restored(self):
        _, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        manager = coordinator.cover_manager
        until = NOW + timedelta(days=2)
        await manager.async_inhibit(["cover.a"], until)
        await manager.async_inhibit(["cover.b"], None)
        saved = manager._store.async_save.call_args.args[0]
        assert saved["inhibited"] == {"cover.a": until.isoformat(), "cover.b": None}

        _, restored = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        restored.cover_manager._store.async_load = AsyncMock(
            return_value={**saved, "inhibited": {**saved["inhibited"], "cover.c": "garbage"}}
        )
        await restored.cover_manager.async_restore_state()

        assert restored.cover_manager._inhibited == {"cover.a": until, "cover.b": None}

    def test_managed_covers_lists_daily_then_heat(self):
        _, coordinator = _coordinator(
            {
                CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b"),
                CONF_COVER_ENTITIES: ["cover.b", "cover.heat"],
            }
        )
        assert coordinator.managed_covers == ["cover.a", "cover.b", "cover.heat"]

    def test_managed_covers_accepts_a_single_heat_cover_string(self):
        _, coordinator = _coordinator({CONF_COVER_ENTITIES: "cover.heat"})
        assert coordinator.managed_covers == ["cover.heat"]


class TestDailyScheduleSkipsInhibited:
    """The daily open/close leaves inhibited covers alone."""

    async def test_open_skips_inhibited_cover(self):
        hass, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        manager = coordinator.cover_manager
        await manager.async_inhibit(["cover.b"], None)

        await manager.async_check_daily_schedule(NOW.replace(hour=8, minute=30))

        assert _calls(hass) == [("cover", "open_cover", ["cover.a"])]

    async def test_open_with_every_cover_inhibited_sends_nothing_and_is_not_caught_up(self):
        hass, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a")})
        manager = coordinator.cover_manager
        await manager.async_inhibit(["cover.a"], NOW.replace(hour=10))

        await manager.async_check_daily_schedule(NOW.replace(hour=8, minute=30))
        assert _calls(hass) == []
        assert manager._daily_opened_date == date(2026, 7, 1)

        # The inhibition ended at 10:00: the morning open is not replayed.
        await manager.async_check_daily_schedule(NOW.replace(hour=11))
        assert _calls(hass) == []

    async def test_close_skips_inhibited_cover_without_reporting_it_left_open(self):
        hass, coordinator = _coordinator(
            {
                CONF_DAILY_COVER_ITEMS: _items(
                    "cover.a", "cover.b", "cover.c",
                    window={"cover.b": "binary_sensor.window_b"},
                    button={"cover.c": "button.my_c"},
                )
            }
        )
        open_window = MagicMock()
        open_window.state = "on"
        hass.states.get.side_effect = lambda entity_id: open_window
        manager = coordinator.cover_manager
        manager._daily_opened_date = date(2026, 7, 1)
        await manager.async_inhibit(["cover.b", "cover.c"], None)

        await manager.async_check_daily_schedule(NOW.replace(hour=21, minute=40))

        assert _calls(hass) == [("cover", "close_cover", ["cover.a"])]
        assert manager.covers_left_open == {}

    async def test_inhibited_cover_resumes_at_next_action(self):
        hass, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a")})
        manager = coordinator.cover_manager
        manager._daily_opened_date = date(2026, 7, 1)
        await manager.async_inhibit(["cover.a"], NOW.replace(hour=18))

        await manager.async_check_daily_schedule(NOW.replace(hour=21, minute=40))

        assert _calls(hass) == [("cover", "close_cover", ["cover.a"])]


class TestManualActionsSkipInhibited:
    """Open/close now leave inhibited covers where they are."""

    async def test_open_now_skips_inhibited(self, monkeypatch):
        monkeypatch.setattr("custom_components.homeshift.cover_manager.dt_util.now", lambda: NOW)
        hass, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        await coordinator.cover_manager.async_inhibit(["cover.b"], None)

        assert await coordinator.cover_manager.async_open_covers_now() is True

        assert _calls(hass) == [("cover", "open_cover", ["cover.a"])]

    async def test_open_now_with_every_cover_inhibited_sends_nothing(self, monkeypatch):
        monkeypatch.setattr("custom_components.homeshift.cover_manager.dt_util.now", lambda: NOW)
        hass, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a")})
        await coordinator.cover_manager.async_inhibit(["cover.a"], None)

        assert await coordinator.cover_manager.async_open_covers_now() is True

        assert _calls(hass) == []

    async def test_close_now_skips_inhibited(self, monkeypatch):
        monkeypatch.setattr("custom_components.homeshift.cover_manager.dt_util.now", lambda: NOW)
        hass, coordinator = _coordinator({CONF_DAILY_COVER_ITEMS: _items("cover.a", "cover.b")})
        await coordinator.cover_manager.async_inhibit(["cover.a"], None)

        assert await coordinator.cover_manager.async_close_covers_now() is True

        assert _calls(hass) == [("cover", "close_cover", ["cover.b"])]


class TestHeatProtectionSkipsInhibited:
    """Heat protection leaves inhibited covers alone."""

    def _hot(self, hass):
        hot = MagicMock()
        hot.state = "35"
        hass.states.get.side_effect = lambda entity_id: hot

    def _options(self, covers, **extra):
        return {
            CONF_COVER_ENTITIES: covers,
            CONF_COVER_TEMP_SENSOR: "sensor.temp",
            CONF_COVER_TEMP_THRESHOLD: 30.0,
            **extra,
        }

    async def test_closes_only_the_covers_not_inhibited(self):
        hass, coordinator = _coordinator(self._options(["cover.a", "cover.b"]))
        self._hot(hass)
        await coordinator.cover_manager.async_inhibit(["cover.a"], None)

        await coordinator.cover_manager.async_check_heat_protection(NOW)

        assert _calls(hass) == [("cover", "close_cover", ["cover.b"])]

    async def test_every_cover_inhibited_does_nothing_and_stays_armed(self):
        hass, coordinator = _coordinator(self._options(["cover.a"]))
        self._hot(hass)
        manager = coordinator.cover_manager
        await manager.async_inhibit(["cover.a"], NOW + timedelta(hours=1))

        await manager.async_check_heat_protection(NOW)
        assert _calls(hass) == []
        assert manager._heat_closed is False

        await manager.async_check_heat_protection(NOW + timedelta(hours=2))
        assert _calls(hass) == [("cover", "close_cover", ["cover.a"])]

    async def test_my_button_not_pressed_while_one_of_its_covers_is_inhibited(self):
        hass, coordinator = _coordinator(
            self._options(["cover.a", "cover.b"], **{CONF_COVER_MY_BUTTON: "button.my"})
        )
        self._hot(hass)
        await coordinator.cover_manager.async_inhibit(["cover.a"], None)

        await coordinator.cover_manager.async_check_heat_protection(NOW)

        assert _calls(hass) == []


class TestInhibitionEnd:
    """The end of an inhibit_covers call."""

    def test_duration(self, monkeypatch):
        monkeypatch.setattr("custom_components.homeshift.dt_util.now", lambda: NOW)
        assert _inhibition_end({ATTR_DURATION: timedelta(days=3)}) == NOW + timedelta(days=3)

    def test_until_without_zone_is_read_in_local_zone(self, monkeypatch):
        monkeypatch.setattr("custom_components.homeshift.dt_util.now", lambda: NOW)
        monkeypatch.setattr("custom_components.homeshift.dt_util.get_default_time_zone", lambda: TZ)
        assert _inhibition_end({ATTR_UNTIL: datetime(2026, 7, 4, 8, 0)}) == datetime(2026, 7, 4, 8, 0, tzinfo=TZ)

    def test_no_end_means_until_resumed(self):
        assert _inhibition_end({}) is None

    @pytest.mark.parametrize(
        "data",
        [{ATTR_DURATION: timedelta(0)}, {ATTR_UNTIL: NOW - timedelta(hours=1)}],
    )
    def test_end_in_the_past_is_refused(self, monkeypatch, data):
        monkeypatch.setattr("custom_components.homeshift.dt_util.now", lambda: NOW)
        with pytest.raises(ServiceValidationError):
            _inhibition_end(data)
