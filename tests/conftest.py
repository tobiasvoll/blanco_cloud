"""Common fixtures for the BLANCO Cloud tests."""

from __future__ import annotations

from collections.abc import Generator
import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from blanco_smart_home_api_client import BlancoApiClient, BlancoErrorType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blanco_cloud.const import (
    CONF_APP_ID,
    CONF_DEV_ID,
    CONF_DEV_TYPE,
    CONF_SERIAL_NUMBER,
    CONF_TOKEN,
    CONF_TOKEN_TYPE,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

SERIAL = "005276602540C20634"
SERVICE_CODE = "12345"
DEV_ID = BlancoApiClient.compute_dev_id(SERIAL, SERVICE_CODE)
APP_ID = "app-123"
INFO = {"dev_type": 2, "online": 1793291944655, "connected": True}

SYSTEM = {
    "params": {
        "dev_name": "CHOICE.All-634",
        "sw_ver_main_con": "R161506",
        "sw_ver_comm_con": "1.5.10",
    },
    "info": INFO,
}
STATUS = {"params": {"co2_rest": 10, "filter_rest": 0}, "info": INFO}
SETTINGS = {
    "params": {
        "child_protect": False,
        "set_point_heating": 100,
        "set_point_cooling": 6,
        "absence_mode_active": False,
    },
    "info": INFO,
}
ERRORS = {
    "errors": [
        {
            "err_code": "2190",
            "err_type": BlancoErrorType.WARNING,
            "err_ts": 1793291887705,
        },
        {"err_code": "2230", "err_type": BlancoErrorType.INFO, "err_ts": 1793291887705},
    ],
    "info": INFO,
}
STATS = {
    "ranges": [
        {
            "range": {"from": 0, "to": 1},
            "total": [
                {"par": "disp_wtr_amt", "func": 3, "cnt": 47, "val": 12338},
                {
                    "par": "tap_state",
                    "func": 5,
                    "cnt": 12338,
                    "val": [
                        {"cnt": 2311, "val": 1},
                        {"cnt": 9327, "val": 3},
                        {"cnt": 700, "val": 4},
                    ],
                },
                {"par": "wtr_flow", "func": 3, "cnt": 0, "val": 0},
            ],
            "details": [],
        }
    ],
    "info": INFO,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Enable custom integrations defined in the test dir."""
    return enable_custom_integrations


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Replace the API client with a mock returning the data of a CHOICE.ALL."""
    client = MagicMock()
    client.register_app = AsyncMock(return_value={"app_id": APP_ID})
    client.authenticate = AsyncMock(
        return_value={"token": "token", "token_type": "Bearer", "dev_type": 2}
    )
    client.deregister_app = AsyncMock()
    client.get_device_system = AsyncMock(return_value=(200, copy.deepcopy(SYSTEM)))
    client.get_device_status = AsyncMock(return_value=(200, copy.deepcopy(STATUS)))
    client.get_device_settings = AsyncMock(return_value=(200, copy.deepcopy(SETTINGS)))
    client.get_device_errors = AsyncMock(return_value=(200, copy.deepcopy(ERRORS)))
    client.get_device_stats = AsyncMock(return_value=(200, copy.deepcopy(STATS)))
    with patch(
        "custom_components.blanco_cloud.api.BlancoApiClient", return_value=client
    ) as client_class:
        client.client_class = client_class
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry of a CHOICE.ALL."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="CHOICE.ALL 0634",
        unique_id=DEV_ID,
        data={
            CONF_SERIAL_NUMBER: SERIAL,
            CONF_DEV_ID: DEV_ID,
            CONF_APP_ID: APP_ID,
            CONF_TOKEN: "token",
            CONF_TOKEN_TYPE: "Bearer",
            CONF_DEV_TYPE: 2,
        },
    )
