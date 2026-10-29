"""Diagnostics of the BLANCO Cloud integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_APP_ID, CONF_DEV_ID, CONF_SERIAL_NUMBER, CONF_TOKEN
from .coordinator import BlancoCloudConfigEntry

TO_REDACT = {CONF_APP_ID, CONF_DEV_ID, CONF_SERIAL_NUMBER, CONF_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BlancoCloudConfigEntry
) -> dict[str, Any]:
    """Return the entry and the last data from the cloud."""
    data = asdict(entry.runtime_data.data)
    data["water_today"] = {
        (water_type.name.lower() if water_type else "total"): amount
        for water_type, amount in entry.runtime_data.data.water_today.items()
    }
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "data": data,
    }
