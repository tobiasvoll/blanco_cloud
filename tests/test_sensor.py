"""Tests for the sensors and binary sensors."""

from unittest.mock import MagicMock

from blanco_smart_home_api_client import BlancoWaterType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blanco_cloud.coordinator import water_by_type
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import DEV_ID, STATS  # noqa: TID251


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_sensor_values(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test the values the sensors show for a CHOICE.ALL."""
    await _setup(hass, mock_config_entry)

    expected = {
        "sensor.choice_all_634_co2_remaining": "10",
        "sensor.choice_all_634_filter_remaining": "0",
        "sensor.choice_all_634_cooling_temperature": "6",
        "sensor.choice_all_634_heating_temperature": "100",
        "sensor.choice_all_634_water_today": "12.338",
        "sensor.choice_all_634_still_water_today": "2.311",
        "sensor.choice_all_634_medium_water_today": "0.0",
        "sensor.choice_all_634_classic_water_today": "9.327",
        "sensor.choice_all_634_hot_water_today": "0.7",
        "sensor.choice_all_634_messages": "2",
        "sensor.choice_all_634_last_online": "2026-10-29T16:39:04+00:00",
        "binary_sensor.choice_all_634_connectivity": "on",
        "binary_sensor.choice_all_634_problem": "on",
        "binary_sensor.choice_all_634_child_lock": "off",
        "binary_sensor.choice_all_634_absence_mode": "off",
    }
    for entity_id, state in expected.items():
        assert hass.states.get(entity_id).state == state, entity_id

    messages = hass.states.get("sensor.choice_all_634_messages")
    assert messages.attributes["errors"] == [
        {"code": "2190", "type": "warning", "time": "2026-10-29T16:38:07.705000+00:00"},
        {"code": "2230", "type": "info", "time": "2026-10-29T16:38:07.705000+00:00"},
    ]


async def test_device(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test the device the entities belong to."""
    await _setup(hass, mock_config_entry)
    device = device_registry.async_get_device(identifiers={("blanco_cloud", DEV_ID)})
    assert device.manufacturer == "BLANCO"
    assert device.model == "CHOICE.ALL"
    assert device.name == "CHOICE.All-634"
    assert device.sw_version == "R161506 / 1.5.10"
    assert device.serial_number == "005276602540C20634"


async def test_only_reported_values_get_entities(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that a device without heater gets no heating and hot water sensors."""
    mock_client.get_device_settings.return_value = (
        200,
        {"params": {"set_point_cooling": 6}, "info": {}},
    )
    await _setup(hass, mock_config_entry)

    entity_ids = {
        entry.entity_id
        for entry in er.async_entries_for_config_entry(
            entity_registry, mock_config_entry.entry_id
        )
    }
    assert "sensor.choice_all_634_cooling_temperature" in entity_ids
    assert "sensor.choice_all_634_heating_temperature" not in entity_ids
    assert "sensor.choice_all_634_hot_water_today" not in entity_ids
    assert "binary_sensor.choice_all_634_child_lock" not in entity_ids


def test_water_by_type() -> None:
    """Test reading the dispensed water from the stats."""
    assert water_by_type(STATS) == {
        None: 12338,
        BlancoWaterType.STILL: 2311,
        BlancoWaterType.CLASSIC: 9327,
        BlancoWaterType.HOT: 700,
    }
    assert water_by_type({"ranges": [], "info": {}}) == {None: 0}
    broken = {
        "ranges": [
            {
                "range": {},
                "total": [{"par": "tap_state", "val": [{"cnt": 5, "val": 99}, {}]}],
                "details": [],
            }
        ],
        "info": {},
    }
    assert water_by_type(broken) == {None: 0}
