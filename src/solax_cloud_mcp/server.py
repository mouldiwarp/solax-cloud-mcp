"""MCP server for SolaX Cloud real-time data."""

from mcp.server import Server
from mcp.server.fastmcp import FastMCP

from .client import SolaxApiError, fetch_realtime
from .config import get_default_wifi_sn, get_token_id
from .models import shape_realtime_response

# Validate configuration at import time
TOKEN_ID = get_token_id()

# Initialize the MCP server
server = FastMCP("solax-cloud")


@server.tool()
async def get_realtime_data(wifi_sn: str | None = None) -> dict:
    """Fetch real-time solar inverter data from SolaX Cloud.

    Retrieves the latest readings including power output, energy yields, battery status,
    and grid import/export data from the SolaX Cloud API. All power values are in Watts (W),
    energy in kWh, voltage in Volts (V), current in Amps (A), and temperature in Celsius (°C).

    Args:
        wifi_sn: Registration number of the WiFi/communication dongle to query.
                 If omitted, defaults to SOLAX_WIFI_SN environment variable.

    Returns:
        A structured dictionary with decoded status values and grouped data fields:
        - device: inverter and WiFi module identifiers
        - status: inverter operating status (code + human-readable description)
        - pv: list of active PV strings with voltage/current/power
        - ac: AC output phases and total power
        - energy: yield and grid exchange totals
        - battery: battery voltage/current/power/soc (if equipped)
        - eps: emergency power supply data (if equipped)
        - temperature: device temperature readings
        - meter2: secondary meter data (if equipped)
        - misc: other fields

    Raises:
        ToolError: if credentials are invalid, the device is not found, or the API fails.
    """
    # Resolve wifi_sn: use passed value, fall back to default, raise if neither available
    effective_sn = wifi_sn or get_default_wifi_sn()
    if not effective_sn:
        raise ValueError(
            "No wifiSn provided: either pass wifi_sn argument to this tool or set SOLAX_WIFI_SN environment variable"
        )

    # Fetch raw data from SolaX API
    try:
        raw_result = await fetch_realtime(TOKEN_ID, effective_sn)
    except SolaxApiError as e:
        raise ValueError(f"SolaX API error: {e}") from e

    # Shape the response for the LLM
    shaped = shape_realtime_response(raw_result)
    return shaped


def main() -> None:
    """Run the MCP server."""
    server.run()


if __name__ == "__main__":
    main()
