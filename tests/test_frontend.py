"""Tests for the card bundled with the integration."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.homeshift import frontend
from custom_components.homeshift.const import DOMAIN


async def test_card_is_served_and_loaded_once():
    hass = MagicMock()
    hass.data = {}
    hass.http.async_register_static_paths = AsyncMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))

    with (
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


def test_bundle_is_shipped_with_the_integration():
    bundle = Path(frontend.__file__).parent / "www" / frontend.CARD_FILE
    assert bundle.stat().st_size > 0
