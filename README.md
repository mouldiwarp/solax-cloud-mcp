# SolaX Cloud MCP Server

An MCP server that provides real-time access to solar inverter data from the SolaX Cloud API. Query your inverter's current power output, energy yields, battery status, and grid import/export data directly from Claude Code or Claude Desktop.

## Prerequisites

- **Python 3.10+** (automatically provisioned by `uv`)
- **uv** package manager ([install here](https://astral.sh/uv/))
- A SolaX Cloud account with API access enabled
- WiFi dongle registration number (`wifiSn`) for your inverter

## Getting Started

### 1. Obtain Your SolaX API Credentials

1. Log in to [SolaX Cloud](https://www.solaxcloud.com/user-center/)
2. Navigate to **Service → API**
3. Copy your **tokenId** (keep this secret!)
4. Find your device's **WiFi dongle registration number** in the Device Management section

### 2. Install the Server

```bash
# Clone or navigate to the repo
cd /Users/gary/mysrc/claude/solax-cloud-mcp

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync
```

### 3. Configure Credentials

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and fill in your credentials
nano .env
```

Add your tokenId and WiFi serial number:
```
SOLAX_TOKEN_ID=your_token_here
SOLAX_WIFI_SN=SUT1234VB1
```

### 4. Register with Claude Code

To use this server with Claude Code or Claude Desktop:

```bash
claude mcp add solax-cloud \
  --env SOLAX_TOKEN_ID=your_token_id \
  --env SOLAX_WIFI_SN=your_wifi_sn \
  --scope user \
  -- uv run --directory /Users/gary/mysrc/claude/solax-cloud-mcp solax-cloud-mcp
```

If the above doesn't work (environment variable propagation issues), edit your MCP config JSON directly:
- **Claude Code:** `~/.claude/mcp.json` or project settings
- **Claude Desktop:** `~/.config/Claude/claude_desktop_config.json` (macOS) or equivalent

Add this entry:
```json
{
  "solax-cloud": {
    "command": "uv",
    "args": [
      "run",
      "--directory",
      "/Users/gary/mysrc/claude/solax-cloud-mcp",
      "solax-cloud-mcp"
    ],
    "env": {
      "SOLAX_TOKEN_ID": "your_token_id",
      "SOLAX_WIFI_SN": "your_wifi_sn"
    }
  }
}
```

## Usage

Once registered, the `get_realtime_data` tool is available in your MCP toolset. Use it to query real-time inverter data.

### Tool: `get_realtime_data`

**Arguments:**
- `wifi_sn` (optional): WiFi dongle registration number. If omitted, defaults to `SOLAX_WIFI_SN` environment variable.

**Returns:** A structured dictionary containing:

```json
{
  "device": {
    "inverterSn": "XB422****82041",
    "wifiSn": "SGY****A001",
    "ratedPower_kW": 4.2,
    "uploadTime": "2023-05-26 17:00:09",
    "inverterType": "4"
  },
  "status": {
    "code": "102",
    "description": "Normal"
  },
  "pv": [
    {"string": 1, "current_A": 0.4, "voltage_V": 421.7, "power_W": 189.0},
    {"string": 2, "current_A": 0.0, "voltage_V": 0.0, "power_W": 0.0}
  ],
  "ac": {
    "phases": [
      {"phase": 1, "current_A": 0.9, "voltage_V": 230.1, "power_W": 0.0, "frequency_Hz": 50.03}
    ],
    "totalPower_W": 171.0
  },
  "energy": {
    "yieldToday_kWh": 13.6,
    "yieldTotal_kWh": 31120.6,
    "feedinEnergy_kWh": 0.0,
    "consumeEnergy_kWh": 0.0,
    "pvEnergy_kWh": 0.0,
    "acEnergyIn_kWh": 0.0,
    "feedinPower_W": 0.0
  },
  "battery": {
    "voltage_V": 0.0,
    "current_A": 0.0,
    "power_W": 0.0,
    "soc_percent": 0.0,
    "temperature_C": 0.0,
    "cycles": "0",
    "chargeEnergy_kWh": 0.0,
    "dischargeEnergy_kWh": 0.0,
    "status": {"code": "0", "description": "Normal"}
  },
  "eps": {
    "voltage_V": [0.0, 0.0, 0.0],
    "current_A": [0.0, 0.0, 0.0],
    "power_W": [0.0, 0.0, 0.0],
    "frequency_Hz": 0.0
  },
  "temperature": {
    "radiator_C": 32.0,
    "board_C": 32.0
  }
}
```

### Example Usage in Claude

> "What's the current power output of my solar inverter?"

Claude will call `get_realtime_data()` and report the results to you in human-friendly terms.

## Manual Testing

### Quick Smoke Test

Before registering with Claude, you can test the client directly:

```bash
uv run --env-file .env python -c \
  "import asyncio; from solax_cloud_mcp.client import fetch_realtime; \
   from solax_cloud_mcp.config import get_token_id, get_default_wifi_sn; \
   print(asyncio.run(fetch_realtime(get_token_id(), get_default_wifi_sn())))"
```

### Run Tests

```bash
uv run pytest -v
```

Tests include:
- Response shaping and status decoding
- Environment variable validation
- Error handling

### Interactive Inspection

If you have the MCP CLI tools installed:

```bash
uv run --env-file .env mcp dev src/solax_cloud_mcp/server.py
```

Or with the Node inspector (requires Node.js):

```bash
uv run --env-file .env npx @modelcontextprotocol/inspector \
  -- solax-cloud-mcp
```

## Rate Limiting

This server respects SolaX Cloud's documented rate limits:
- **10 calls per minute** per token
- **10,000 calls per day** per token

The client automatically enforces a 6-second minimum spacing between calls, which keeps typical usage well within both limits. No manual rate limiting is needed.

## Data Fields Reference

All values are in SI units:
- **Power:** Watts (W)
- **Energy:** Kilowatt-hours (kWh)
- **Voltage:** Volts (V)
- **Current:** Amps (A)
- **Temperature:** Celsius (°C)
- **Frequency:** Hertz (Hz)

### Inverter Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 100 | Waiting | Waiting for operation |
| 101 | Self-test | Self-test in progress |
| 102 | Normal | Operating normally |
| 103 | Recoverable | Recoverable fault |
| 104 | Permanent | Permanent fault |
| 105 | Upgrade | Firmware upgrade |
| 106 | EPS Detect | EPS detection |
| 107 | Off-grid | Off-grid operation |
| 108 | Self-test IT | Self-test (Italian regulations) |
| 109 | Sleep | Sleep mode |
| 110 | Standby | Standby mode |
| 111 | PV Wake | Photovoltaic wake-up battery mode |
| 112 | Gen Detect | Generator detection |
| 113 | Generator | Generator mode |
| 114 | Fast Shutdown | Fast shutdown standby |
| 130 | VPP | Virtual Power Plant mode |
| 131 | TOU-Self | Time-of-use self-use mode |
| 132 | TOU-Charge | Time-of-use charging mode |
| 133 | TOU-Discharge | Time-of-use discharging mode |

### Battery Status Codes

| Code | Status |
|------|--------|
| 0 | Normal |
| 1 | Fault |
| 2 | Disconnected |

### API Error Codes

| Code | Message |
|------|---------|
| 1001 | Interface Unauthorized (invalid token) |
| 1002 | Parameter validation failed (invalid wifiSn) |
| 1003 | Data Unauthorized |
| 1004 | Duplicate data |
| 2001 | Operation failed |
| 2002 | Data not found (device not registered) |

## Troubleshooting

**"SOLAX_TOKEN_ID environment variable not set"**
- Set the `SOLAX_TOKEN_ID` environment variable or register the server with the correct credentials

**"No wifiSn provided"**
- Either pass the `wifi_sn` argument to the tool or set the `SOLAX_WIFI_SN` environment variable

**"SolaX API error 1002: Parameter validation failed"**
- The `wifiSn` you provided is invalid. Double-check it in your SolaX Cloud Device Management.

**"SolaX API error 1001: Interface Unauthorized"**
- Your `SOLAX_TOKEN_ID` is invalid or has expired. Generate a new token from SolaX Cloud.

**"Network timeout"**
- SolaX Cloud API is unreachable. Check your internet connection and confirm the service is online.

## Development

### Project Structure

```
solax-cloud-mcp/
├── src/solax_cloud_mcp/
│   ├── __init__.py         # Package metadata
│   ├── __main__.py         # CLI entry point
│   ├── server.py           # MCP server and tool definitions
│   ├── client.py           # HTTP client and SolaX API calls
│   ├── config.py           # Environment variable handling
│   └── models.py           # Data models and response shaping
├── tests/
│   ├── fixtures/           # Test data
│   ├── test_models.py      # Response shaping tests
│   └── test_config.py      # Configuration tests
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # This file
```

### Adding Features

The server is designed to be minimal and focused. To add more endpoints/tools:

1. Fetch the data from SolaX Cloud API (extend `client.py`)
2. Add a response shaping function if needed (extend `models.py`)
3. Define a new `@server.tool()` in `server.py`

## License

MIT

## Support

For issues with this MCP server, open an issue on the repository.

For SolaX Cloud API documentation, refer to [SolaX Cloud](https://www.solaxcloud.com/).
