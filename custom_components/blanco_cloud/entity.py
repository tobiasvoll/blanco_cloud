"""Base entity of the BLANCO Cloud integration."""

from __future__ import annotations

from blanco_smart_home_api_client import device_model_name

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEV_TYPE, CONF_SERIAL_NUMBER, DOMAIN
from .coordinator import BlancoCloudCoordinator


class BlancoCloudEntity(CoordinatorEntity[BlancoCloudCoordinator]):
    """An entity of one BLANCO device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: BlancoCloudCoordinator, description: EntityDescription
    ) -> None:
        """Attach the entity to the device of the config entry."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        system = coordinator.data.system
        self._attr_unique_id = f"{coordinator.dev_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.dev_id)},
            manufacturer="BLANCO",
            model=device_model_name(entry.data[CONF_DEV_TYPE]),
            name=system.get("dev_name") or entry.title,
            serial_number=entry.data.get(CONF_SERIAL_NUMBER),
            # the main controller and the communication (WiFi) controller
            sw_version=" / ".join(
                version
                for version in (
                    system.get("sw_ver_main_con"),
                    system.get("sw_ver_comm_con"),
                )
                if version
            )
            or None,
        )
