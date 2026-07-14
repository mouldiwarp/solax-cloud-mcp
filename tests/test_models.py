"""Tests for data models and response shaping."""

import json
import pytest

from solax_cloud_mcp.models import (
    BATTERY_STATUS_DESCRIPTIONS,
    ERROR_CODE_DESCRIPTIONS,
    INVERTER_STATUS_DESCRIPTIONS,
    shape_realtime_response,
)


@pytest.fixture
def fixture_response():
    """Load the sample API response from the fixture file."""
    with open("tests/fixtures/realtime_success.json") as f:
        data = json.load(f)
    return data["result"]


def test_shape_realtime_response_structure(fixture_response):
    """Test that shaped response has all expected top-level keys."""
    shaped = shape_realtime_response(fixture_response)

    expected_keys = {
        "device",
        "status",
        "pv",
        "ac",
        "energy",
        "battery",
        "eps",
        "temperature",
        "meter2",
        "misc",
    }
    assert set(shaped.keys()) == expected_keys


def test_inverter_status_decoding(fixture_response):
    """Test that inverter status code 102 decodes to 'Normal'."""
    shaped = shape_realtime_response(fixture_response)

    assert shaped["status"]["code"] == "102"
    assert shaped["status"]["description"] == "Normal"


def test_battery_status_decoding(fixture_response):
    """Test that battery status code '0' decodes to 'Normal'."""
    shaped = shape_realtime_response(fixture_response)

    assert shaped["battery"]["status"]["code"] == "0"
    assert shaped["battery"]["status"]["description"] == "Normal"


def test_pv_strings_exclude_nulls(fixture_response):
    """Test that null/unused PV strings are excluded from the pv list."""
    shaped = shape_realtime_response(fixture_response)

    # fixture has idc3=null, idc4=null, so only strings 1 and 2 should be included
    assert len(shaped["pv"]) == 2
    assert shaped["pv"][0]["string"] == 1
    assert shaped["pv"][1]["string"] == 2
    assert shaped["pv"][0]["current_A"] == 0.4
    assert shaped["pv"][1]["current_A"] == 0.0


def test_ac_phases_structure(fixture_response):
    """Test AC phases are grouped correctly."""
    shaped = shape_realtime_response(fixture_response)

    ac_data = shaped["ac"]
    assert "phases" in ac_data
    assert "totalPower_W" in ac_data
    assert ac_data["totalPower_W"] == 171.0


def test_energy_fields_passthrough(fixture_response):
    """Test energy fields are correctly mapped."""
    shaped = shape_realtime_response(fixture_response)

    assert shaped["energy"]["yieldToday_kWh"] == 13.6
    assert shaped["energy"]["yieldTotal_kWh"] == 31120.6


def test_battery_fields_passthrough(fixture_response):
    """Test battery fields are correctly mapped."""
    shaped = shape_realtime_response(fixture_response)

    battery = shaped["battery"]
    assert battery["voltage_V"] == 0.0
    assert battery["soc_percent"] == 0.0
    assert battery["temperature_C"] == 0.0


def test_device_fields(fixture_response):
    """Test device identifier fields."""
    shaped = shape_realtime_response(fixture_response)

    device = shaped["device"]
    assert device["inverterSn"] == "XB422****82041"
    assert device["wifiSn"] == "SGY****A001"
    assert device["ratedPower_kW"] == 4.2
    assert device["uploadTime"] == "2023-05-26 17:00:09"


def test_error_code_descriptions():
    """Test that all documented error codes are in the lookup."""
    expected_codes = {1001, 1002, 1003, 1004, 2001, 2002}
    assert set(ERROR_CODE_DESCRIPTIONS.keys()) == expected_codes


def test_inverter_status_descriptions():
    """Test that all documented inverter statuses are in the lookup."""
    # Spot check a few
    assert INVERTER_STATUS_DESCRIPTIONS["102"] == "Normal"
    assert INVERTER_STATUS_DESCRIPTIONS["103"] == "Recoverable fault"
    assert INVERTER_STATUS_DESCRIPTIONS["131"] == "TOU-Self use"


def test_battery_status_descriptions():
    """Test battery status lookup."""
    assert BATTERY_STATUS_DESCRIPTIONS["0"] == "Normal"
    assert BATTERY_STATUS_DESCRIPTIONS["1"] == "Fault"
    assert BATTERY_STATUS_DESCRIPTIONS["2"] == "Disconnected"
