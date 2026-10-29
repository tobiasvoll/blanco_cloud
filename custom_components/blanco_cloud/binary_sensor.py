"""Binary sensors of the BLANCO Cloud integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BlancoCloudConfigEntry, BlancoCloudData
from .entity import BlancoCloudEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BlancoCloudBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a binary sensor and where its value comes from."""

    value_fn: Callable[[BlancoCloudData], bool | None]
    exists_fn: Callable[[BlancoCloudData], bool] = lambda _: True


def _setting(key: str) -> BlancoCloudBinarySensorEntityDescription:
    """Describe a sensor showing an on/off setting the device reports."""
    return BlancoCloudBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        value_fn=lambda data: data.settings.get(key),
        exists_fn=lambda data: key in data.settings,
    )


BINARY_SENSORS: tuple[BlancoCloudBinarySensorEntityDescription, ...] = (
    BlancoCloudBinarySensorEntityDescription(
        key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.info.get("connected"),
    ),
    BlancoCloudBinarySensorEntityDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.has_problem,
    ),
    _setting("child_protect"),
    _setting("absence_mode_active"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BlancoCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the binary sensors the device reports values for."""
    coordinator = entry.runtime_data
    async_add_entities(
        BlancoCloudBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.exists_fn(coordinator.data)
    )


class BlancoCloudBinarySensor(BlancoCloudEntity, BinarySensorEntity):
    """An on/off state of the BLANCO device."""

    entity_description: BlancoCloudBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the current state."""
        return self.entity_description.value_fn(self.coordinator.data)
