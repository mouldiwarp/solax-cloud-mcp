"""CLI entry point with transport mode selection."""

import os

if __name__ == "__main__":
    transport = os.getenv("TRANSPORT", "stdio").lower()

    if transport == "http":
        from .http_server import main
    elif transport == "stdio":
        from .server import main
    else:
        raise ValueError(
            f"Invalid TRANSPORT mode: {transport}. Must be 'stdio' (default) or 'http'"
        )

    main()
