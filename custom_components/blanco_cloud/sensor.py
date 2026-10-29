"""Sensors of the BLANCO Cloud integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from blanco_smart_home_api_client import BlancoWaterType

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .coordinator import BlancoCloudConfigEntry, BlancoCloudData
from .entity import BlancoCloudEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BlancoCloudSensorEntityDescription(SensorEntityDescription):
    """Describe a sensor and where its value comes from."""

    value_fn: Callable[[BlancoCloudData], StateType | datetime]
    exists_fn: Callable[[BlancoCloudData], bool] = lambda _: True
    attributes_fn: Callable[[BlancoCloudData], dict[str, Any]] | None = None


def _param(section: str, key: str, **kwargs: Any) -> BlancoCloudSensorEntityDescription:
    """Describe a sensor showing a parameter of one section of the cloud data.

    The sensor only exists if the device reports that parameter.
    """
    return BlancoCloudSensorEntityDescription(
        key=key,
        translation_key=key,
        value_fn=lambda data: getattr(data, section).get(key),
        exists_fn=lambda data: key in getattr(data, section),
        **kwargs,
    )


def _water(
    key: str, water_type: BlancoWaterType | None, **kwargs: Any
) -> BlancoCloudSensorEntityDescription:
    """Describe the water dispensed today, of one type or in total (None)."""
    return BlancoCloudSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: data.water_today.get(water_type, 0) / 1000,
        **kwargs,
    )


def _online(data: BlancoCloudData) -> datetime | None:
    """Return when the device was last online."""
    online = data.info.get("online")
    if not isinstance(online, int):
        return None
    return dt_util.utc_from_timestamp(online / 1000)


def _error_attributes(data: BlancoCloudData) -> dict[str, Any]:
    """List the reported errors with their severity and time."""
    return {
        "errors": [
            {
                "code": error["err_code"],
                "type": error["err_type"].name.lower(),
                "time": dt_util.utc_from_timestamp(error["err_ts"] / 1000).isoformat()
                if error["err_ts"]
                else None,
            }
            for error in data.errors
        ]
    }


SENSORS: tuple[BlancoCloudSensorEntityDescription, ...] = (
    _param(
        "status",
        "co2_rest",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _param(
        "status",
        "filter_rest",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _param(
        "settings",
        "set_point_cooling",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    _param(
        "settings",
        "set_point_heating",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    _water("water_today", None),
    _water("still_water_today", BlancoWaterType.STILL),
    _water("medium_water_today", BlancoWaterType.MEDIUM),
    _water("classic_water_today", BlancoWaterType.CLASSIC),
    # only devices with a heater, like the CHOICE.ALL, dispense hot water
    _water(
        "hot_water_today",
        BlancoWaterType.HOT,
        exists_fn=lambda data: "set_point_heating" in data.settings,
    ),
    BlancoCloudSensorEntityDescription(
        key="errors",
        translation_key="errors",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.errors),
        attributes_fn=_error_attributes,
    ),
    BlancoCloudSensorEntityDescription(
        key="last_online",
        translation_key="last_online",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_online,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BlancoCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors the device reports values for."""
    coordinator = entry.runtime_data
    async_add_entities(
        BlancoCloudSensor(coordinator, description)
        for description in SENSORS
        if description.exists_fn(coordinator.data)
    )


class BlancoCloudSensor(BlancoCloudEntity, SensorEntity):
    """A value of the BLANCO device."""

    entity_description: BlancoCloudSensorEntityDescription

    @property
    def native_value(self) -> StateType | datetime:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra details of the value, if any."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
