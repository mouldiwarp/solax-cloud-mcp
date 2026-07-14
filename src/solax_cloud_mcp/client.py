"""HTTP client for SolaX Developer Platform API."""

import asyncio
import time

import httpx

from . import auth
from .models import ERROR_CODE_DESCRIPTIONS

BASE_URL = "https://openapi-eu.solaxcloud.com"
REALTIME_DATA_URL = f"{BASE_URL}/openapi/v2/device/realtime_data"

DEVICE_TYPE_INVERTER = 1
DEVICE_TYPE_BATTERY = 2
BUSINESS_TYPE_RESIDENTIAL = 1
REQUEST_SN_TYPE_INVERTER = 1

_last_call_at = 0.0
_rate_limit_lock = asyncio.Lock()
MIN_INTERVAL_SECONDS = 0.7  # 60s / 100 calls per minute, conservative buffer


class SolaxApiError(Exception):
    """Raised when the SolaX API returns an error."""

    pass


async def _request_realtime(
    device_sn: str, device_type: int, request_sn_type: int | None
) -> dict | None:
    """Internal: make a single realtime data request to the API.

    Args:
        device_sn: Device serial number.
        device_type: Device type (1=Inverter, 2=Battery, etc.).
        request_sn_type: Optional, only used for deviceType=2 (battery).

    Returns:
        The first result dict if available, else None (empty result list).

    Raises:
        SolaxApiError: on network errors, non-10000 code, or other failures.
    """
    global _last_call_at

    # Rate limiting
    async with _rate_limit_lock:
        elapsed = time.monotonic() - _last_call_at
        if elapsed < MIN_INTERVAL_SECONDS:
            await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        _last_call_at = time.monotonic()

    # Build query params
    params = {
        "snList": device_sn,
        "deviceType": device_type,
        "businessType": BUSINESS_TYPE_RESIDENTIAL,
    }
    if request_sn_type is not None:
        params["requestSnType"] = request_sn_type

    # Get access token and make request
    try:
        token = await auth.get_access_token()
    except auth.SolaxAuthError as e:
        raise SolaxApiError(f"Authentication failed: {e}") from e

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                REALTIME_DATA_URL,
                params=params,
                headers={"Authorization": f"bearer {token}"},
            )
        except httpx.TimeoutException as e:
            raise SolaxApiError(f"Network timeout: {e}") from e
        except httpx.RequestError as e:
            raise SolaxApiError(f"Network error: {e}") from e

        # Check HTTP status
        if response.status_code != 200:
            raise SolaxApiError(
                f"HTTP {response.status_code}: {response.text}"
            )

        # Parse JSON
        try:
            body = response.json()
        except ValueError as e:
            raise SolaxApiError(f"Invalid JSON response: {e}") from e

        # Check API response code (10000 = success for data endpoints)
        code = body.get("code")
        if code == 10402:
            # Access token auth failed; invalidate and retry once
            auth.invalidate_token()
            try:
                token = await auth.get_access_token()
            except auth.SolaxAuthError as e:
                raise SolaxApiError(f"Re-authentication failed after 10402: {e}") from e

            try:
                response = await client.get(
                    REALTIME_DATA_URL,
                    params=params,
                    headers={"Authorization": f"bearer {token}"},
                )
            except httpx.RequestError as e:
                raise SolaxApiError(f"Retry after 10402 failed: {e}") from e

            if response.status_code != 200:
                raise SolaxApiError(f"Retry: HTTP {response.status_code}: {response.text}")

            try:
                body = response.json()
            except ValueError as e:
                raise SolaxApiError(f"Retry: Invalid JSON: {e}") from e

            code = body.get("code")

    if code != 10000:
        description = ERROR_CODE_DESCRIPTIONS.get(code, f"Unknown code {code}")
        raise SolaxApiError(f"API error {code}: {description}")

    # Extract result list
    result = body.get("result")
    if not result:
        # Empty result list most likely means device is offline/no data yet
        return None
    if isinstance(result, list) and len(result) > 0:
        return result[0]
    return None


async def fetch_inverter_data(device_sn: str) -> dict:
    """Fetch inverter real-time data.

    Args:
        device_sn: Inverter serial number.

    Returns:
        The inverter data dict.

    Raises:
        SolaxApiError: if the call fails or returns no data.
    """
    result = await _request_realtime(device_sn, DEVICE_TYPE_INVERTER, None)
    if result is None:
        raise SolaxApiError(f"No inverter data returned for device_sn={device_sn}")
    return result


async def fetch_battery_data(device_sn: str) -> dict | None:
    """Fetch battery real-time data for an inverter.

    Swallows errors and returns None if no battery data is available,
    as this is likely just a battery-less system.

    Args:
        device_sn: Inverter serial number (queries battery associated with this inverter).

    Returns:
        The battery data dict, or None if unavailable or an error occurred.
    """
    try:
        return await _request_realtime(device_sn, DEVICE_TYPE_BATTERY, REQUEST_SN_TYPE_INVERTER)
    except SolaxApiError:
        # Battery-specific failure likely means no battery on this system
        return None


async def fetch_realtime_data(device_sn: str) -> tuple[dict, dict | None]:
    """Fetch both inverter and battery real-time data.

    Args:
        device_sn: Inverter serial number.

    Returns:
        A tuple of (inverter_data, battery_data_or_none).

    Raises:
        SolaxApiError: if the inverter call fails (battery errors are swallowed).
    """
    inverter_data = await fetch_inverter_data(device_sn)
    battery_data = await fetch_battery_data(device_sn)
    return inverter_data, battery_data
