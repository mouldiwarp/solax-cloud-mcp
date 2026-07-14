"""Data models, enums, and response shaping."""

INVERTER_STATUS_DESCRIPTIONS = {
    "100": "Waiting for operation",
    "101": "Self-test",
    "102": "Normal",
    "103": "Recoverable fault",
    "104": "Permanent fault",
    "105": "Firmware upgrade",
    "106": "EPS detection",
    "107": "Off-grid",
    "108": "Self-test mode (Italian)",
    "109": "Sleep mode",
    "110": "Standby mode",
    "111": "Photovoltaic wake-up battery mode",
    "112": "Generator detection mode",
    "113": "Generator mode",
    "114": "Fast shutdown standby mode",
    "130": "VPP mode",
    "131": "TOU-Self use",
    "132": "TOU-Charging",
    "133": "TOU-Discharging",
}

BATTERY_STATUS_DESCRIPTIONS = {
    "0": "Normal",
    "1": "Fault",
    "2": "Disconnected",
}

ERROR_CODE_DESCRIPTIONS = {
    1001: "Interface Unauthorized",
    1002: "Parameter validation failed",
    1003: "Data Unauthorized",
    1004: "Duplicate data",
    2001: "Operation failed",
    2002: "Data not found",
}


def shape_realtime_response(raw_result: dict) -> dict:
    """Transform raw SolaX API response into a human-friendly, grouped structure.

    Args:
        raw_result: The 'result' object from a successful SolaX realtimeInfo response.

    Returns:
        A dictionary with grouped, decoded fields suitable for LLM consumption.
    """
    # Extract PV strings, dropping those with null values (unused MPPT trackers)
    pv_strings = []
    for i in range(1, 5):
        idc_key = f"idc{i}"
        vdc_key = f"vdc{i}"
        powerdc_key = f"powerdc{i}"
        if idc_key in raw_result and raw_result[idc_key] is not None:
            pv_strings.append({
                "string": i,
                "current_A": raw_result.get(idc_key),
                "voltage_V": raw_result.get(vdc_key),
                "power_W": raw_result.get(powerdc_key),
            })

    # Extract AC phases, dropping those with all-zero values
    ac_phases = []
    for i in range(1, 4):
        iac_key = f"iac{i}"
        vac_key = f"vac{i}"
        pac_key = f"pac{i}"
        fac_key = f"fac{i}"
        iac = raw_result.get(iac_key, 0)
        vac = raw_result.get(vac_key, 0)
        pac = raw_result.get(pac_key, 0)
        fac = raw_result.get(fac_key, 0)
        if any([iac, vac, pac, fac]):
            ac_phases.append({
                "phase": i,
                "current_A": iac,
                "voltage_V": vac,
                "power_W": pac,
                "frequency_Hz": fac,
            })

    # Extract inverter status
    inverter_status_code = str(raw_result.get("inverterStatus", ""))
    inverter_status = {
        "code": inverter_status_code,
        "description": INVERTER_STATUS_DESCRIPTIONS.get(
            inverter_status_code, "Unknown"
        ),
    }

    # Extract battery status
    battery_status_code = str(raw_result.get("batStatus", ""))
    battery_status = {
        "code": battery_status_code,
        "description": BATTERY_STATUS_DESCRIPTIONS.get(battery_status_code, "Unknown"),
    }

    return {
        "device": {
            "inverterSn": raw_result.get("inverterSn"),
            "wifiSn": raw_result.get("sn"),
            "ratedPower_kW": raw_result.get("ratedPower"),
            "uploadTime": raw_result.get("uploadTime"),
            "inverterType": raw_result.get("inverterType"),
        },
        "status": inverter_status,
        "pv": pv_strings,
        "ac": {
            "phases": ac_phases,
            "totalPower_W": raw_result.get("acpower"),
        },
        "energy": {
            "yieldToday_kWh": raw_result.get("yieldtoday"),
            "yieldTotal_kWh": raw_result.get("yieldtotal"),
            "feedinEnergy_kWh": raw_result.get("feedinenergy"),
            "consumeEnergy_kWh": raw_result.get("consumeenergy"),
            "pvEnergy_kWh": raw_result.get("pvenergy"),
            "acEnergyIn_kWh": raw_result.get("acenergyin"),
            "feedinPower_W": raw_result.get("feedinpower"),
        },
        "battery": {
            "voltage_V": raw_result.get("batVoltage"),
            "current_A": raw_result.get("batCurrent"),
            "power_W": raw_result.get("batPower"),
            "soc_percent": raw_result.get("soc"),
            "temperature_C": raw_result.get("battemper"),
            "cycles": raw_result.get("batcycle"),
            "chargeEnergy_kWh": raw_result.get("chargeEnergy"),
            "dischargeEnergy_kWh": raw_result.get("dischargeEnergy"),
            "status": battery_status,
        },
        "eps": {
            "voltage_V": [
                raw_result.get("veps1"),
                raw_result.get("veps2"),
                raw_result.get("veps3"),
            ],
            "current_A": [
                raw_result.get("ieps1"),
                raw_result.get("ieps2"),
                raw_result.get("ieps3"),
            ],
            "power_W": [
                raw_result.get("peps1"),
                raw_result.get("peps2"),
                raw_result.get("peps3"),
            ],
            "frequency_Hz": raw_result.get("epsfreq"),
        },
        "temperature": {
            "radiator_C": raw_result.get("temperature"),
            "board_C": raw_result.get("temperBoard"),
        },
        "meter2": {
            "feedinPower_W": raw_result.get("feedinpowerM2"),
            "feedinEnergy_kWh": raw_result.get("feedinenergyM2"),
            "consumeEnergy_kWh": raw_result.get("consumeenergyM2"),
        },
        "misc": {
            "surplusEnergy_percent": raw_result.get("surplusEnergy"),
            "timeZone": raw_result.get("timeZone"),
        },
    }
