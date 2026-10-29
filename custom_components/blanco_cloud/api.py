"""Build the BLANCO Smart Home API client for a config entry."""

from __future__ import annotations

from collections.abc import Callable

from blanco_smart_home_api_client import BlancoApiClient

from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import VERSION


def create_client(
    hass: HomeAssistant,
    *,
    app_id: str = "",
    token: str = "",
    token_type: str = "Bearer",
    dev_id: str = "",
    on_token_renewed: Callable[[str, str], None] | None = None,
) -> BlancoApiClient:
    """Return a client that identifies itself as this integration."""
    return BlancoApiClient(
        async_get_clientsession(hass),
        app_id=app_id,
        token=token,
        token_type=token_type,
        dev_id=dev_id,
        app_version=VERSION,
        app_build="1",
        os_version=HA_VERSION,
        on_token_renewed=on_token_renewed,
    )
