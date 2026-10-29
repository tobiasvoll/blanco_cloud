"""Tests for setting up and removing the integration."""

from datetime import timedelta
from unittest.mock import MagicMock

from blanco_smart_home_api_client import (
    BlancoAuthError,
    BlancoConnectionError,
    BlancoTokenExpiredError,
)
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.blanco_cloud.const import CONF_TOKEN, DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import APP_ID, DEV_ID  # noqa: TID251


async def test_setup_and_unload(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that the entry is set up with the stored credentials and unloaded."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    kwargs = mock_client.client_class.call_args.kwargs
    assert kwargs["app_id"] == APP_ID
    assert kwargs["token"] == "token"
    assert kwargs["dev_id"] == DEV_ID

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_remove_deregisters_app(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that removing the entry removes the app registration, even if that fails."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    mock_client.deregister_app.side_effect = BlancoConnectionError

    await hass.config_entries.async_remove(mock_config_entry.entry_id)

    mock_client.deregister_app.assert_awaited_once()


async def test_setup_retry_on_connection_error(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that setup is retried when the cloud cannot be reached."""
    mock_client.get_device_system.side_effect = BlancoConnectionError
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize("exception", [BlancoAuthError, BlancoTokenExpiredError])
async def test_revoked_access_starts_reauth(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    exception: type[Exception],
) -> None:
    """Test that a revoked access asks the user to reauthenticate."""
    mock_client.get_device_status.side_effect = exception
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH


async def test_failed_update_makes_entities_unavailable(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the entities become unavailable when an update fails."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert hass.states.get("sensor.choice_all_634_co2_remaining").state == "10"

    mock_client.get_device_stats.side_effect = BlancoConnectionError
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        hass.states.get("sensor.choice_all_634_co2_remaining").state
        == STATE_UNAVAILABLE
    )


async def test_renewed_token_is_stored(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that a token the client renewed is kept in the entry."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)

    on_token_renewed = mock_client.client_class.call_args.kwargs["on_token_renewed"]
    on_token_renewed("renewed", "Bearer")

    assert mock_config_entry.data[CONF_TOKEN] == "renewed"
