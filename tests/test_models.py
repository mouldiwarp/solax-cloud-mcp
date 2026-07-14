"""Tests for data models and response shaping."""

import json
import pytest

from solax_cloud_mcp.models import (
    BATTERY_DEVICE_STATUS_DESCRIPTIONS,
    ERROR_CODE_DESCRIPTIONS,
    INVERTER_DEVICE_STATUS_DESCRIPTIONS,
    shape_realtime_response,
)


@pytest.fixture
def inverter_fixture():
    """Load the inverter API response from the fixture file."""
    with open("tests/fixtures/inverter_realtime_success.json") as f:
        data = json.load(f)
    return data["result"][0]


@pytest.fixture
def battery_fixture():
    """Load the battery API response from the fixture file."""
    with open("tests/fixtures/battery_realtime_success.json") as f:
        data = json.load(f)
    return data["result"][0]


def test_shape_realtime_response_structure(inverter_fixture, battery_fixture):
    """Test that shaped response has all expected top-level keys."""
    shaped = shape_realtime_response(inverter_fixture, battery_fixture)

    expected_keys = {
        "device",
        "status",
        "pv",
        "mppt",
        "ac",
        "energy",
        "meter1",
        "meter2",
        "battery",
        "eps",
        "temperature",
        "misc",
    }
    assert set(shaped.keys()) == expected_keys


def test_shape_realtime_response_battery_none(inverter_fixture):
    """Test that battery=None doesn't raise and produces None in output."""
    shaped = shape_realtime_response(inverter_fixture, None)
    assert shaped["battery"] is None


def test_inverter_status_decoding(inverter_fixture):
    """Test that inverter status code None produces 'Not reported'."""
    shaped = shape_realtime_response(inverter_fixture, None)
    assert shaped["status"]["code"] is None
    assert shaped["status"]["description"] == "Not reported"


def test_battery_status_decoding(battery_fixture, inverter_fixture):
    """Test that battery status code 1 decodes to 'Work'."""
    shaped = shape_realtime_response(inverter_fixture, battery_fixture)
    assert shaped["battery"]["status"]["code"] == 1
    assert shaped["battery"]["status"]["description"] == "Work"


def test_pv_strings_dynamic_parsing(inverter_fixture):
    """Test that PV strings are dynamically parsed from pvMap."""
    shaped = shape_realtime_response(inverter_fixture, None)
    pv = shaped["pv"]
    # Fixture has pv1, pv2 with data, pv3-4 with all null
    assert len(pv) == 2
    assert pv[0]["string"] == 1
    assert pv[0]["current_A"] == 0.4
    assert pv[0]["voltage_V"] == 421.7
    assert pv[1]["string"] == 2
    assert pv[1]["current_A"] == 0.0


def test_mppt_dynamic_parsing(inverter_fixture):
    """Test that MPPT trackers are dynamically parsed from mpptMap."""
    shaped = shape_realtime_response(inverter_fixture, None)
    mppt = shaped["mppt"]
    # Fixture has mppt1 and mppt2, both all zeros
    assert "trackers" in mppt
    assert "totalPower_W" in mppt


def test_ac_phases_structure(inverter_fixture):
    """Test AC phases are correctly structured."""
    shaped = shape_realtime_response(inverter_fixture, None)
    ac_data = shaped["ac"]
    assert "phases" in ac_data
    assert "totalPower_W" in ac_data
    assert "totalReactivePower" in ac_data
    assert "powerFactor" in ac_data
    assert "gridFrequency" in ac_data


def test_energy_fields_passthrough(inverter_fixture):
    """Test energy fields are correctly mapped."""
    shaped = shape_realtime_response(inverter_fixture, None)
    assert shaped["energy"]["dailyYield_kWh"] == 157.4
    assert shaped["energy"]["totalYield_kWh"] == 20465.3


def test_battery_fields_passthrough(battery_fixture, inverter_fixture):
    """Test battery fields are correctly mapped."""
    shaped = shape_realtime_response(inverter_fixture, battery_fixture)
    battery = shaped["battery"]
    assert battery["soc_percent"] == 85.5
    assert battery["voltage_V"] == 409.6
    assert battery["temperature_C"] == 28.3


def test_device_fields(inverter_fixture):
    """Test device identifier fields."""
    shaped = shape_realtime_response(inverter_fixture, None)
    device = shaped["device"]
    assert device["deviceSn"] == "X3ABCD0123"
    assert device["registerNo"] == "SE123456SP"
    assert device["plantLocalTime"] == "2025-05-22 15:13:10"


def test_eps_casing_normalized(inverter_fixture):
    """Test that EPS fields with mixed casing (EPSL1Voltage) are correctly extracted."""
    shaped = shape_realtime_response(inverter_fixture, None)
    eps = shaped["eps"]
    # Fixture uses uppercase EPSL1Voltage, lowercase normalization should handle this
    assert eps["voltage_V"][0] == 0.0
    assert eps["current_A"][0] == 0.0


def test_error_code_descriptions():
    """Test that all documented error codes are in the lookup."""
    expected_codes = {
        10000, 10001, 11500, 10200, 10400, 10401, 10402, 10403, 10404, 10405, 10406, 10500, 10505, 10506
    }
    assert set(ERROR_CODE_DESCRIPTIONS.keys()) == expected_codes


def test_inverter_status_descriptions():
    """Test that all documented inverter statuses are in the lookup."""
    # Spot check a few
    assert INVERTER_DEVICE_STATUS_DESCRIPTIONS[100] == "Waiting"
    assert INVERTER_DEVICE_STATUS_DESCRIPTIONS[102] == "Normal"
    assert INVERTER_DEVICE_STATUS_DESCRIPTIONS[131] == "TOU-Self use"
    assert INVERTER_DEVICE_STATUS_DESCRIPTIONS[1309] == "PV&BAT Individual Setting-Target SOC Mode"


def test_battery_status_descriptions():
    """Test battery status lookup."""
    assert BATTERY_DEVICE_STATUS_DESCRIPTIONS[0] == "Idle"
    assert BATTERY_DEVICE_STATUS_DESCRIPTIONS[1] == "Work"


def test_device_status_none_handled(inverter_fixture):
    """Test that deviceStatus=None is handled gracefully."""
    # Fixture already has deviceStatus=null; verify it produces "Not reported"
    shaped = shape_realtime_response(inverter_fixture, None)
    assert shaped["status"]["description"] == "Not reported"


def test_battery_totalcharge_field_typo(battery_fixture, inverter_fixture):
    """Test that the typo'd totalDevicharg field is read correctly."""
    # The docs have a typo: totalDevicharg instead of totalDeviceCharge
    shaped = shape_realtime_response(inverter_fixture, battery_fixture)
    assert shaped["battery"]["totalCharge_kWh"] == 4250.75
