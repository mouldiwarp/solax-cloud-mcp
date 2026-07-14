"""HTTP client for SolaX Cloud API."""

import asyncio
import time
from typing import Any

import httpx

from .models import ERROR_CODE_DESCRIPTIONS

API_URL = "https://global.solaxcloud.com/api/v2/dataAccess/realtimeInfo/get"

_last_call_at = 0.0
_rate_limit_lock = asyncio.Lock()
MIN_INTERVAL_SECONDS = 6.0  # 60s / 10 calls per minute


class SolaxApiError(Exception):
    """Raised when the SolaX API returns an error."""

    pass


async def fetch_realtime(token_id: str, wifi_sn: str) -> dict:
    """Fetch real-time data from SolaX Cloud API.

    Args:
        token_id: SolaX Cloud API token.
        wifi_sn: WiFi dongle registration number.

    Returns:
        The 'result' object from the API response.

    Raises:
        SolaxApiError: if the API call fails for any reason.
    """
    global _last_call_at

    # Rate limiting: enforce minimum spacing between calls
    async with _rate_limit_lock:
        elapsed = time.monotonic() - _last_call_at
        if elapsed < MIN_INTERVAL_SECONDS:
            await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        _last_call_at = time.monotonic()

    # Make the request
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                API_URL,
                headers={"tokenId": token_id},
                json={"wifiSn": wifi_sn},
            )
    except httpx.TimeoutException as e:
        raise SolaxApiError(f"Network timeout contacting SolaX Cloud: {e}") from e
    except httpx.RequestError as e:
        raise SolaxApiError(f"Network error contacting SolaX Cloud: {e}") from e

    # Check HTTP status
    if response.status_code != 200:
        raise SolaxApiError(
            f"SolaX API returned HTTP {response.status_code}: {response.text}"
        )

    # Parse and validate JSON
    try:
        body = response.json()
    except ValueError as e:
        raise SolaxApiError(f"Invalid JSON response from SolaX API: {e}") from e

    # Check success flag
    if not body.get("success"):
        code = body.get("code", 0)
        description = ERROR_CODE_DESCRIPTIONS.get(code, "Unknown error")
        raise SolaxApiError(
            f"SolaX API error {code}: {description} "
            f"(exception: {body.get('exception', 'N/A')})"
        )

    # Return the result
    result = body.get("result")
    if not result:
        raise SolaxApiError("SolaX API response missing result field")

    return result
