"""Serve and load the HomeShift Lovelace card bundled with the integration."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "homeshift-card.js"
CARD_URL_PATH = f"/{DOMAIN}/{CARD_FILE}"
# Built from frontend/ and shipped in the release archive (homeshift.zip);
# a git checkout does not have it until `npm run build` is run.
CARD_PATH = Path(__file__).parent / "www" / CARD_FILE
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

    digest = await hass.async_add_executor_job(_digest, CARD_PATH)
    if not digest:
        # Loading a missing script would break every dashboard's console with
        # a 404; the integration itself works without its card.
        _LOGGER.warning(
            "The HomeShift card is missing (%s): install HomeShift from a release, "
            "or build it with `npm ci && npm run build` in frontend/, then restart Home Assistant",
            CARD_PATH,
        )
        return

    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(CARD_PATH), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={integration.version}-{digest}")
