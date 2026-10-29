"""Constants for the BLANCO Cloud integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "blanco_cloud"
VERSION: Final = "0.1.0"

CONF_SERIAL_NUMBER: Final = "serial_number"
CONF_SERVICE_CODE: Final = "service_code"
CONF_DEV_ID: Final = "dev_id"
CONF_APP_ID: Final = "app_id"
CONF_TOKEN: Final = "token"
CONF_TOKEN_TYPE: Final = "token_type"
CONF_DEV_TYPE: Final = "dev_type"

UPDATE_INTERVAL: Final = timedelta(minutes=5)
