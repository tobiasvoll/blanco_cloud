"""Tests for the diagnostics."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from homeassistant.core import HomeAssistant


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the diagnostics hide the credentials."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    entry = result["entry"]
    for key in ("app_id", "dev_id", "serial_number", "token"):
        assert entry[key] == "**REDACTED**"
    assert result["data"]["status"] == {"co2_rest": 10, "filter_rest": 0}
    assert result["data"]["water_today"] == {
        "total": 12338,
        "still": 2311,
        "classic": 9327,
        "hot": 700,
    }
