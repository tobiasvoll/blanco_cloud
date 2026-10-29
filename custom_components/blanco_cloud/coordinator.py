"""Poll the BLANCO Cloud for the data of one device."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from blanco_smart_home_api_client import (
    BlancoApiClient,
    BlancoApiError,
    BlancoAuthError,
    BlancoErrorType,
    BlancoTokenExpiredError,
    BlancoWaterType,
    DeviceErrorItem,
    DeviceStatsResult,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import create_client
from .const import (
    CONF_APP_ID,
    CONF_DEV_ID,
    CONF_TOKEN,
    CONF_TOKEN_TYPE,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type BlancoCloudConfigEntry = ConfigEntry[BlancoCloudCoordinator]


@dataclass
class BlancoCloudData:
    """Everything the cloud reports about the device."""

    system: dict[str, Any]
    status: dict[str, Any]
    settings: dict[str, Any]
    info: dict[str, Any]
    errors: list[DeviceErrorItem]
    # millilitres dispensed since local midnight, per water type and in total
    water_today: dict[BlancoWaterType | None, int] = field(default_factory=dict)

    @property
    def has_problem(self) -> bool:
        """Return True if the device reports a warning or a critical error."""
        return any(
            error["err_type"] in (BlancoErrorType.CRITICAL, BlancoErrorType.WARNING)
            for error in self.errors
        )


def water_by_type(stats: DeviceStatsResult) -> dict[BlancoWaterType | None, int]:
    """Return the dispensed millilitres of the first stats range.

    The total is stored under None, every water type under its BlancoWaterType.
    """
    result: dict[BlancoWaterType | None, int] = {None: 0}
    if not stats["ranges"]:
        return result
    for total in stats["ranges"][0]["total"]:
        if total.get("par") == "disp_wtr_amt" and isinstance(total.get("val"), int):
            result[None] = total["val"]
        elif total.get("par") == "tap_state" and isinstance(total.get("val"), list):
            for item in total["val"]:
                try:
                    result[BlancoWaterType(item["val"])] = item["cnt"]
                except (KeyError, ValueError, TypeError):
                    continue
    return result


class BlancoCloudCoordinator(DataUpdateCoordinator[BlancoCloudData]):
    """Fetch the device data from the BLANCO Cloud."""

    config_entry: BlancoCloudConfigEntry

    def __init__(self, hass: HomeAssistant, entry: BlancoCloudConfigEntry) -> None:
        """Create the coordinator and its API client."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.dev_id: str = entry.data[CONF_DEV_ID]
        self.client: BlancoApiClient = create_client(
            hass,
            app_id=entry.data[CONF_APP_ID],
            token=entry.data[CONF_TOKEN],
            token_type=entry.data[CONF_TOKEN_TYPE],
            dev_id=self.dev_id,
            on_token_renewed=self._store_token,
        )

    @callback
    def _store_token(self, token: str, token_type: str) -> None:
        """Keep a renewed token so a restart does not need a new one."""
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_TOKEN: token,
                CONF_TOKEN_TYPE: token_type,
            },
        )

    async def _async_update_data(self) -> BlancoCloudData:
        """Fetch all endpoints the integration shows."""
        now = dt_util.now()
        midnight = dt_util.start_of_local_day(now)
        try:
            _, system = await self.client.get_device_system(self.dev_id)
            _, status = await self.client.get_device_status(self.dev_id)
            _, settings = await self.client.get_device_settings(self.dev_id)
            _, errors = await self.client.get_device_errors(self.dev_id)
            _, stats = await self.client.get_device_stats(
                self.dev_id,
                [
                    {
                        "from": int(midnight.timestamp() * 1000),
                        "to": int(now.timestamp() * 1000),
                    }
                ],
            )
        except (BlancoAuthError, BlancoTokenExpiredError) as err:
            # a token can no longer be renewed once the access is revoked
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="access_revoked"
            ) from err
        except BlancoApiError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        return BlancoCloudData(
            system=system["params"],
            status=status["params"],
            settings=settings["params"],
            info=system["info"],
            errors=errors["errors"],
            water_today=water_by_type(stats),
        )
