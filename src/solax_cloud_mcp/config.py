"""Configuration and environment variable handling."""

import os


def get_token_id() -> str:
    """Get the SolaX Cloud API token from environment.

    Raises:
        RuntimeError: if SOLAX_TOKEN_ID is not set.
    """
    token = os.getenv("SOLAX_TOKEN_ID")
    if not token:
        raise RuntimeError(
            "SOLAX_TOKEN_ID environment variable not set. "
            "Obtain your token from https://www.solaxcloud.com/user-center/ "
            "(Service → API menu)."
        )
    return token


def get_default_wifi_sn() -> str | None:
    """Get the default WiFi dongle serial number from environment.

    Returns:
        The SOLAX_WIFI_SN value if set, None otherwise.
    """
    return os.getenv("SOLAX_WIFI_SN")
