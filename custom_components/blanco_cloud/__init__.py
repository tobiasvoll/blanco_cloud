"""The BLANCO Cloud integration."""

from __future__ import annotations

import contextlib

from blanco_smart_home_api_client import BlancoApiError

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import create_client
from .const import CONF_APP_ID
from .coordinator import BlancoCloudConfigEntry, BlancoCloudCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BlancoCloudConfigEntry) -> bool:
    """Set up a BLANCO device from a config entry."""
    coordinator = BlancoCloudCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BlancoCloudConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, entry: BlancoCloudConfigEntry
) -> None:
    """Remove the app registration of this installation from the BLANCO Cloud."""
    client = create_client(hass, app_id=entry.data[CONF_APP_ID])
    # the entry is removed anyway, a stale registration does no harm
    with contextlib.suppress(BlancoApiError):
        await client.deregister_app()
