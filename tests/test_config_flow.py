"""Tests for the config flow."""

from unittest.mock import MagicMock

from blanco_smart_home_api_client import (
    BlancoApiError,
    BlancoAuthError,
    BlancoConnectionError,
    BlancoDeviceTypeError,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blanco_cloud.const import (
    CONF_APP_ID,
    CONF_DEV_ID,
    CONF_DEV_TYPE,
    CONF_SERIAL_NUMBER,
    CONF_SERVICE_CODE,
    CONF_TOKEN,
    CONF_TOKEN_TYPE,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import APP_ID, DEV_ID, SERIAL, SERVICE_CODE  # noqa: TID251

USER_INPUT = {CONF_SERIAL_NUMBER: f" {SERIAL} ", CONF_SERVICE_CODE: SERVICE_CODE}


async def test_user_flow(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """Test that a device is set up with the serial number and service code."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CHOICE.ALL 0634"
    assert result["result"].unique_id == DEV_ID
    assert result["data"] == {
        CONF_SERIAL_NUMBER: SERIAL,
        CONF_DEV_ID: DEV_ID,
        CONF_APP_ID: APP_ID,
        CONF_TOKEN: "token",
        CONF_TOKEN_TYPE: "Bearer",
        CONF_DEV_TYPE: 2,
    }
    mock_client.register_app.assert_awaited_once_with("en")
    mock_client.update_app_id.assert_called_once_with(APP_ID)
    mock_client.authenticate.assert_awaited_once_with(DEV_ID)


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (BlancoAuthError, "not_granted"),
        (BlancoDeviceTypeError, "unsupported_device"),
        (BlancoConnectionError, "cannot_connect"),
        (BlancoApiError, "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_client: MagicMock,
    exception: type[Exception],
    error: str,
) -> None:
    """Test that a failed authentication shows an error and can be retried."""
    mock_client.authenticate.side_effect = exception
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_client.authenticate.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that a device is not set up twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_client.register_app.assert_not_awaited()


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that reauthentication keeps the app registration and stores the token."""
    mock_config_entry.add_to_hass(hass)
    mock_client.authenticate.return_value = {
        "token": "new-token",
        "token_type": "Bearer",
        "dev_type": 2,
    }
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    mock_client.authenticate.side_effect = BlancoAuthError
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_granted"}

    mock_client.authenticate.side_effect = None
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_TOKEN] == "new-token"
    assert mock_config_entry.data[CONF_APP_ID] == APP_ID
    mock_client.register_app.assert_not_awaited()
    # the entry is reloaded with the new token
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
