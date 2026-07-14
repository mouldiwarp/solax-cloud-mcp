"""OAuth2 token lifecycle management for SolaX Developer Platform."""

import asyncio
import time

import httpx

from . import config

TOKEN_URL = "https://openapi-eu.solaxcloud.com/openapi/auth/oauth/token"
EXPIRY_BUFFER_SECONDS = 300

_cached_token: str | None = None
_expires_at: float = 0.0
_auth_lock = asyncio.Lock()


class SolaxAuthError(Exception):
    """Raised when OAuth2 authentication fails."""

    pass


async def get_access_token() -> str:
    """Get a valid access token, fetching a new one if needed.

    Automatically refreshes the token if it will expire within the buffer period.
    Thread-safe via internal locking.

    Returns:
        A valid OAuth2 access token.

    Raises:
        SolaxAuthError: if token fetch/refresh fails.
    """
    global _cached_token, _expires_at

    async with _auth_lock:
        # Double-check: if we still have time on the cached token, return it
        if _cached_token and time.monotonic() < _expires_at - EXPIRY_BUFFER_SECONDS:
            return _cached_token

        # Otherwise, fetch a new token
        token, expires_in = await _fetch_new_token()
        _cached_token = token
        _expires_at = time.monotonic() + expires_in
        return token


def invalidate_token() -> None:
    """Clear the cached token, forcing a re-fetch on next access.

    Called by client.py when a 10402 (access_token auth failure) is received.
    """
    global _cached_token, _expires_at
    _cached_token = None
    _expires_at = 0.0


async def _fetch_new_token() -> tuple[str, float]:
    """Fetch a fresh access token from the OAuth2 endpoint.

    Returns:
        A tuple of (access_token, expires_in_seconds).

    Raises:
        SolaxAuthError: on network errors, non-200 HTTP, unparseable JSON,
            auth failure (code != 0), or missing fields in response.
    """
    client_id = config.get_client_id()
    client_secret = config.get_client_secret()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
            )
    except Exception as e:
        raise SolaxAuthError(f"Network error during token fetch: {e}") from e

    if response.status_code != 200:
        raise SolaxAuthError(
            f"Token endpoint returned HTTP {response.status_code}: {response.text}"
        )

    try:
        body = response.json()
    except Exception as e:
        raise SolaxAuthError(f"Failed to parse token response JSON: {e}") from e

    # Auth endpoint uses code==0 for success, NOT code==10000 (unlike other endpoints)
    if body.get("code") != 0:
        raise SolaxAuthError(
            f"Token fetch failed: code={body.get('code')}, message={body.get('message')}"
        )

    result = body.get("result")
    if not result:
        raise SolaxAuthError("Token response missing 'result' field")

    access_token = result.get("access_token")
    expires_in = result.get("expires_in")

    if not access_token:
        raise SolaxAuthError("Token response missing 'access_token' in result")
    if expires_in is None:
        raise SolaxAuthError("Token response missing 'expires_in' in result")

    return access_token, expires_in
