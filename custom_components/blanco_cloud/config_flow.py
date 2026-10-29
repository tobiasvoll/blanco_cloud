"""Config flow for the BLANCO Cloud integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from blanco_smart_home_api_client import (
    BlancoApiClient,
    BlancoApiError,
    BlancoAuthError,
    BlancoConnectionError,
    BlancoDeviceTypeError,
    device_model_name,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import create_client
from .const import (
    CONF_APP_ID,
    CONF_DEV_ID,
    CONF_DEV_TYPE,
    CONF_SERIAL_NUMBER,
    CONF_SERVICE_CODE,
    CONF_TOKEN,
    CONF_TOKEN_TYPE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_NUMBER): TextSelector(),
        vol.Required(CONF_SERVICE_CODE): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class BlancoCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a BLANCO device that shares its data with the BLANCO Cloud."""

    VERSION = 1

    async def _async_authenticate(
        self, dev_id: str, app_id: str | None
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Register this installation if needed and get a token for dev_id.

        Returns the entry data to store and the form errors.
        """
        client = create_client(self.hass, app_id=app_id or "")
        try:
            if not app_id:
                app_id = (await client.register_app(self.hass.config.language))[
                    "app_id"
                ]
                client.update_app_id(app_id)
            auth = await client.authenticate(dev_id)
        except BlancoAuthError:
            return {}, {"base": "not_granted"}
        except BlancoDeviceTypeError:
            return {}, {"base": "unsupported_device"}
        except BlancoConnectionError:
            return {}, {"base": "cannot_connect"}
        except BlancoApiError:
            _LOGGER.exception("Unexpected response from the BLANCO Cloud")
            return {}, {"base": "unknown"}
        return {
            CONF_DEV_ID: dev_id,
            CONF_APP_ID: app_id,
            CONF_TOKEN: auth["token"],
            CONF_TOKEN_TYPE: auth["token_type"],
            CONF_DEV_TYPE: auth["dev_type"],
        }, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the serial number and service code shown in the UNIT app."""
        errors: dict[str, str] = {}
        if user_input is not None:
            serial = user_input[CONF_SERIAL_NUMBER].strip()
            service_code = user_input[CONF_SERVICE_CODE].strip()
            dev_id = BlancoApiClient.compute_dev_id(serial, service_code)
            await self.async_set_unique_id(dev_id)
            self._abort_if_unique_id_configured()

            data, errors = await self._async_authenticate(dev_id, None)
            if not errors:
                model = device_model_name(data[CONF_DEV_TYPE]) or "BLANCO"
                return self.async_create_entry(
                    title=f"{model} {serial[-4:]}",
                    data={CONF_SERIAL_NUMBER: serial, **data},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the cloud access was revoked."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Retry once the user granted access in the UNIT app again."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data, errors = await self._async_authenticate(
                entry.data[CONF_DEV_ID], entry.data.get(CONF_APP_ID)
            )
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_show_form(step_id="reauth_confirm", errors=errors)
