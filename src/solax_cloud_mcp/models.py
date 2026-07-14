"""Data models, enums, and response shaping."""

ERROR_CODE_DESCRIPTIONS = {
    10000: "Operation successful",
    10001: "Operation failed",
    11500: "System busy, please try again later",
    10200: "Operation abnormality, please see the specific message content for details",
    10400: "Request not authenticated",
    10401: "Username or password incorrect",
    10402: "Request access_token authentication failed",
    10403: "Interface has no access rights",
    10404: "Callback function not configured",
    10405: "The number of API calls has been used up",
    10406: "The API call rate has reached the upper limit, please try again later",
    10500: "User has no device data permission",
    10505: "Device unauthorized",
    10506: "Plant unauthorized",
}

INVERTER_DEVICE_STATUS_DESCRIPTIONS = {
    100: "Waiting",
    101: "Self-check",
    102: "Normal",
    103: "Fault",
    104: "Permanent Fault Mode",
    105: "Update Mode",
    106: "EPS Check Mode",
    107: "EPS Mode",
    108: "Self-test",
    109: "Idle Mode",
    110: "Standby Mode",
    111: "Pv Wake Up Bat Mode",
    112: "Gen Check Mode",
    113: "Gen run Mode",
    114: "RSD Standby",
    130: "VPP mode",
    131: "TOU-Self use",
    132: "TOU-Charging",
    133: "TOU-Discharging",
    134: "TOU-Battery off",
    135: "TOU-Peak Shaving",
    136: "Normal Mode(Gen)",
    137: "Normal Mode(BAT-E)",
    138: "Normal Mode(BAT-H)",
    139: "EPS mode(BAT-H)",
    140: "Start Mode",
    141: "Normal Mode(R-1)",
    142: "Normal Mode(R-2)",
    143: "Normal Mode(R-3)",
    144: "Normal Mode(R-4)",
    145: "Normal Mode(R-5)",
    146: "Normal Mode(R-6)",
    147: "Normal Mode(R-7)",
    150: "Self Use",
    151: "Force Time Use",
    152: "Back Up Mode",
    153: "Feedin Priority",
    154: "Demand Mode",
    155: "ConstPowr Mode",
    160: "OpenAdr Mode",
    170: "STOP MODE",
    171: "DEBUG MODE",
    174: "Normal(Smart selfuse)",
    175: "Normal(Smart feedin)",
    176: "Normal(Smart Bat not discharge)",
    177: "Normal(WLV 0%)",
    1301: "Power Control Mode",
    1302: "Electric Quantity Target Control Mode",
    1303: "SOC Target Control Mode",
    1304: "Push Power -Positive/Negative Mode",
    1305: "Push Power - Zero Mode",
    1306: "Self-Consume -Charge/Discharge Mode",
    1307: "Self-Consume - Charge Only Mode",
    1308: "PV&BAT Individual Setting- Duration Mode",
    1309: "PV&BAT Individual Setting-Target SOC Mode",
}

BATTERY_DEVICE_STATUS_DESCRIPTIONS = {
    0: "Idle",
    1: "Work",
}


def shape_realtime_response(inverter_result: dict, battery_result: dict | None) -> dict:
    """Transform raw SolaX Developer Platform API responses into a human-friendly structure.

    Args:
        inverter_result: The inverter device data dict from the realtime_data endpoint.
        battery_result: The battery device data dict, or None if no battery data available.

    Returns:
        A dictionary with grouped, decoded fields suitable for LLM consumption.
    """
    # Normalize all keys to lowercase for case-insensitive access
    # (docs show mixed casing inconsistency: field table says epsl1Voltage, example shows EPSL1Voltage)
    inverter = {k.lower(): v for k, v in inverter_result.items()}
    mppt_map = inverter.get("mpptmap", {})
    if isinstance(mppt_map, dict):
        mppt_map = {k.lower(): v for k, v in mppt_map.items()}
    pv_map = inverter.get("pvmap", {})
    if isinstance(pv_map, dict):
        pv_map = {k.lower(): v for k, v in pv_map.items()}

    # Dynamic PV string parsing: extract pv{N}voltage, pv{N}current, pv{N}power
    pv_strings = []
    pv_indices = set()
    for key in pv_map.keys():
        if key.startswith("pv") and any(key.endswith(s) for s in ["voltage", "current", "power"]):
            # Extract index: pv1voltage -> 1
            idx_str = key[2:-7]  # Remove 'pv' prefix and '_voltage/_current/_power' suffix
            try:
                idx = int(idx_str)
                pv_indices.add(idx)
            except ValueError:
                pass

    for idx in sorted(pv_indices):
        voltage = pv_map.get(f"pv{idx}voltage")
        current = pv_map.get(f"pv{idx}current")
        power = pv_map.get(f"pv{idx}power")
        # Drop if all three are None/null
        if voltage is not None or current is not None or power is not None:
            pv_strings.append({
                "string": idx,
                "voltage_V": voltage,
                "current_A": current,
                "power_W": power,
            })

    # Dynamic MPPT tracking: extract mppt{N}voltage, mppt{N}current, mppt{N}power
    mppt_trackers = []
    mppt_indices = set()
    for key in mppt_map.keys():
        if key.startswith("mppt") and any(key.endswith(s) for s in ["voltage", "current", "power"]):
            idx_str = key[4:-7]
            try:
                idx = int(idx_str)
                mppt_indices.add(idx)
            except ValueError:
                pass

    for idx in sorted(mppt_indices):
        voltage = mppt_map.get(f"mppt{idx}voltage")
        current = mppt_map.get(f"mppt{idx}current")
        power = mppt_map.get(f"mppt{idx}power")
        if voltage is not None or current is not None or power is not None:
            mppt_trackers.append({
                "mppt": idx,
                "voltage_V": voltage,
                "current_A": current,
                "power_W": power,
            })

    # Extract AC phases (fixed 3-phase), drop if all-zero
    ac_phases = []
    for phase in range(1, 4):
        v_key = f"acvoltage{phase}"
        i_key = f"accurrent{phase}"
        p_key = f"acpower{phase}"
        f_key = f"acfrequency{phase}"
        v = inverter.get(v_key, 0)
        i = inverter.get(i_key, 0)
        p = inverter.get(p_key, 0)
        f = inverter.get(f_key, 0)
        if any([v, i, p, f]):
            ac_phases.append({
                "phase": phase,
                "voltage_V": v,
                "current_A": i,
                "power_W": p,
                "frequency_Hz": f,
            })

    # Inverter status: deviceStatus is now an int or null
    device_status = inverter.get("devicestatus")
    inverter_status = {
        "code": device_status,
        "description": (
            INVERTER_DEVICE_STATUS_DESCRIPTIONS.get(device_status, f"Unknown status code {device_status}")
            if device_status is not None
            else "Not reported"
        ),
    }

    # Battery section: None if no battery_result, else build battery object
    battery = None
    if battery_result is not None:
        battery_dict = {k.lower(): v for k, v in battery_result.items()}
        battery_status_code = battery_dict.get("devicestatus")
        battery = {
            "soc_percent": battery_dict.get("batterysoc"),
            "remainingEnergy_kWh": battery_dict.get("batteryremainings"),
            "soh_percent": battery_dict.get("batterysoh"),
            "chargeDischargePower_W": battery_dict.get("chargedischargepower"),
            "voltage_V": battery_dict.get("batteryvoltage"),
            "current_A": battery_dict.get("batterycurrent"),
            "temperature_C": battery_dict.get("batterytemperature"),
            "cycleTimes": battery_dict.get("batterycycletimes"),
            "totalCharge_kWh": battery_dict.get("totaldevicharg"),
            "totalDischarge_kWh": battery_dict.get("totaldevicedischarge"),
            "status": {
                "code": battery_status_code,
                "description": (
                    BATTERY_DEVICE_STATUS_DESCRIPTIONS.get(battery_status_code, f"Unknown status code {battery_status_code}")
                    if battery_status_code is not None
                    else "Not reported"
                ),
            },
        }

    return {
        "device": {
            "deviceSn": inverter.get("devicesn"),
            "registerNo": inverter.get("registerno"),
            "dataTime": inverter.get("datatime"),
            "plantLocalTime": inverter.get("plantlocaltime"),
        },
        "status": inverter_status,
        "pv": pv_strings,
        "mppt": {
            "trackers": mppt_trackers,
            "totalPower_W": inverter.get("mppttotalinputpower"),
        },
        "ac": {
            "phases": ac_phases,
            "totalPower_W": inverter.get("totalactivepower"),
            "totalReactivePower": inverter.get("totalreactivepower"),
            "powerFactor": inverter.get("totalpowerfactor"),
            "gridFrequency": inverter.get("gridfrequency"),
        },
        "energy": {
            "dailyYield_kWh": inverter.get("dailyyield"),
            "totalYield_kWh": inverter.get("totalyield"),
            "dailyACOutput_kWh": inverter.get("dailyacoutput"),
            "totalACOutput_kWh": inverter.get("totalacoutput"),
        },
        "meter1": {
            "gridPower_W": inverter.get("gridpower"),
            "todayImportEnergy_kWh": inverter.get("todayimportenergy"),
            "totalImportEnergy_kWh": inverter.get("totalimportenergy"),
            "todayExportEnergy_kWh": inverter.get("todayexportenergy"),
            "totalExportEnergy_kWh": inverter.get("totalexportenergy"),
        },
        "meter2": {
            "gridPower_W": inverter.get("gridpowerm2"),
            "todayImportEnergy_kWh": inverter.get("todayimportenergym2"),
            "totalImportEnergy_kWh": inverter.get("totalimportenergym2"),
            "todayExportEnergy_kWh": inverter.get("todayexportenergym2"),
            "totalExportEnergy_kWh": inverter.get("totalexportenergym2"),
        },
        "battery": battery,
        "eps": {
            "voltage_V": [
                inverter.get("epsl1voltage"),
                inverter.get("epsl2voltage"),
                inverter.get("epsl3voltage"),
            ],
            "current_A": [
                inverter.get("epsl1current"),
                inverter.get("epsl2current"),
                inverter.get("epsl3current"),
            ],
            "activePower_W": [
                inverter.get("epsl1activepower"),
                inverter.get("epsl2activepower"),
                inverter.get("epsl3activepower"),
            ],
            "apparentPower_W": [
                inverter.get("epsl1apparentpower"),
                inverter.get("epsl2apparentpower"),
                inverter.get("epsl3apparentpower"),
            ],
        },
        "temperature": {
            "inverter_C": inverter.get("invertertemperature"),
        },
        "misc": {
            "l1l2Voltage_V": inverter.get("l1l2voltage"),
            "l2l3Voltage_V": inverter.get("l2l3voltage"),
            "l1l3Voltage_V": inverter.get("l1l3voltage"),
        },
    }
