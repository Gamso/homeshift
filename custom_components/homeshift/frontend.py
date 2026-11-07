"""Serve and load the HomeShift Lovelace card bundled with the integration."""
from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

CARD_FILE = "homeshift-card.js"
CARD_URL_PATH = f"/{DOMAIN}/{CARD_FILE}"
_REGISTERED_KEY = f"{DOMAIN}_card_registered"


def _digest(path: Path) -> str:
    """Return a short digest of the bundle, "" when it cannot be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return ""


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the card bundle and load it in every dashboard.

    A static path cannot be unregistered, so this runs once per HA run, however
    many times the entry is reloaded. The URL carries the version and a digest
    of the bundle: the browser cache, and a CDN or proxy in front of Home
    Assistant (Cloudflare caches .js files by default), serve a new bundle as
    soon as it changes, even within one version.
    """
    if hass.data.get(_REGISTERED_KEY):
        return
    hass.data[_REGISTERED_KEY] = True

    integration = await async_get_integration(hass, DOMAIN)
    card_path = Path(__file__).parent / "www" / CARD_FILE
    digest = await hass.async_add_executor_job(_digest, card_path)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(card_path), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={integration.version}-{digest}")
