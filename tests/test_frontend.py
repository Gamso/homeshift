"""Tests for the card bundled with the integration."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.homeshift import frontend
from custom_components.homeshift.const import DOMAIN


def _hass() -> MagicMock:
    hass = MagicMock()
    hass.data = {}
    hass.http.async_register_static_paths = AsyncMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    return hass


async def test_card_is_served_and_loaded_once(tmp_path):
    hass = _hass()
    bundle = tmp_path / "homeshift-card.js"
    bundle.write_text("export {};")

    with (
        patch.object(frontend, "CARD_PATH", bundle),
        patch.object(frontend, "async_get_integration", AsyncMock(return_value=MagicMock(version="9.9.9"))),
        patch.object(frontend, "add_extra_js_url") as add_url,
    ):
        await frontend.async_register_card(hass)
        await frontend.async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    (config,) = hass.http.async_register_static_paths.await_args.args[0]
    assert config.url_path == f"/{DOMAIN}/homeshift-card.js"
    assert config.path.endswith("homeshift-card.js")
    digest = frontend._digest(Path(config.path))
    assert len(digest) == 8
    add_url.assert_called_once_with(hass, f"/{DOMAIN}/homeshift-card.js?v=9.9.9-{digest}")


def test_digest_changes_with_the_bundle(tmp_path):
    bundle = tmp_path / "card.js"
    bundle.write_text("a")
    first = frontend._digest(bundle)
    bundle.write_text("b")

    assert frontend._digest(bundle) != first
    assert frontend._digest(tmp_path / "missing.js") == ""


async def test_a_missing_card_is_reported_and_not_loaded(tmp_path, caplog):
    """A git checkout without a build: no 404 script in every dashboard, a warning instead."""
    hass = _hass()

    with (
        patch.object(frontend, "CARD_PATH", tmp_path / "homeshift-card.js"),
        patch.object(frontend, "add_extra_js_url") as add_url,
        caplog.at_level("WARNING"),
    ):
        await frontend.async_register_card(hass)

    hass.http.async_register_static_paths.assert_not_awaited()
    add_url.assert_not_called()
    assert "npm run build" in caplog.text


def test_the_card_path_is_what_the_build_writes():
    rollup = (Path(frontend.__file__).parents[2] / "frontend" / "rollup.config.js").read_text()
    assert "custom_components/homeshift/www/homeshift-card.js" in rollup
    assert frontend.CARD_PATH.name == frontend.CARD_FILE
