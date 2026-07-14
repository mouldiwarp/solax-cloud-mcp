"""MCP server for SolaX Developer Platform real-time data."""

from mcp.server.fastmcp import FastMCP

from .client import SolaxApiError, fetch_realtime_data
from .config import get_client_id, get_client_secret, get_default_device_sn
from .models import shape_realtime_response

# Validate configuration at import time
CLIENT_ID = get_client_id()
CLIENT_SECRET = get_client_secret()

# Initialize the MCP server
server = FastMCP("solax-cloud")


@server.tool()
async def get_realtime_data(device_sn: str | None = None) -> dict:
    """Fetch real-time solar inverter data from SolaX Developer Platform.

    Retrieves the latest readings including power output, energy yields, battery status,
    and grid import/export data from the SolaX Developer Platform API. All power values
    are in Watts (W), energy in kWh, voltage in Volts (V), current in Amps (A),
    and temperature in Celsius (°C).

    Args:
        device_sn: Serial number of the inverter to query (the device SN, not WiFi dongle SN).
                   If omitted, defaults to SOLAX_DEVICE_SN environment variable.

    Returns:
        A structured dictionary with decoded status values and grouped data fields:
        - device: inverter identifiers (SN, registration number, timestamps)
        - status: inverter operating status (code + human-readable description)
        - pv: list of active PV strings with voltage/current/power
        - mppt: MPPT tracker data (individual trackers + total power)
        - ac: AC output phases, total power, reactive power, power factor, grid frequency
        - energy: daily/total yield and AC output
        - meter1: grid power and energy (import/export)
        - meter2: secondary meter data (import/export)
        - battery: battery voltage/current/power/soc/status (None if no battery)
        - eps: emergency power supply data (3-phase voltage/current/power)
        - temperature: inverter temperature
        - misc: line-to-line voltages

    Raises:
        ToolError: if credentials are invalid, the device is not found, or the API fails.
    """
    # Resolve device_sn: use passed value, fall back to default, raise if neither available
    effective_sn = device_sn or get_default_device_sn()
    if not effective_sn:
        raise ValueError(
            "No device_sn provided: either pass device_sn argument to this tool or set SOLAX_DEVICE_SN environment variable"
        )

    # Fetch raw data from SolaX API
    try:
        inverter_raw, battery_raw = await fetch_realtime_data(effective_sn)
    except SolaxApiError as e:
        raise ValueError(f"SolaX API error: {e}") from e

    # Shape the response for the LLM
    shaped = shape_realtime_response(inverter_raw, battery_raw)
    return shaped


def main() -> None:
    """Run the MCP server."""
    server.run()


if __name__ == "__main__":
    main()
