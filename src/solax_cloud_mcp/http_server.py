"""FastAPI HTTP server for SolaX Developer Platform API."""

import os
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from .server import get_realtime_data_impl, set_battery_self_use_mode_impl


def get_api_key() -> str:
    """Get HTTP API key from environment, raise if not set."""
    key = os.getenv("HTTP_API_KEY")
    if not key:
        raise RuntimeError("HTTP_API_KEY environment variable not set")
    return key


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="SolaX Cloud API",
        description="HTTP API for SolaX solar inverter data and control",
        version="0.1.0",
    )
    api_key = get_api_key()

    async def verify_api_key(authorization: Annotated[str, Header()]) -> None:
        """Verify bearer token matches HTTP_API_KEY."""
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization header format. Use: Bearer <token>",
            )
        if credentials != api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )

    # Request/Response models
    class RealtimeDataRequest(BaseModel):
        device_sn: str | None = Field(
            None,
            description="Inverter device serial number. If omitted, uses SOLAX_DEVICE_SN env var.",
        )

    class SetBatterySelfUseModeRequest(BaseModel):
        device_sn: str | None = Field(
            None,
            description="Inverter device serial number. If omitted, uses SOLAX_DEVICE_SN env var.",
        )
        min_soc: int = Field(10, ge=10, le=100, description="Minimum SOC (%)")
        charge_upper_soc: int = Field(100, ge=10, le=100, description="Maximum charging SOC (%)")
        charge_from_grid_enable: int = Field(1, ge=0, le=1, description="Allow grid charging (0=no, 1=yes)")
        charge_start_time_period1: str | None = Field(None, description="Start time (HH:MM format, e.g. 06:00)")
        charge_end_time_period1: str | None = Field(None, description="End time (HH:MM format, e.g. 18:00)")
        discharge_start_time_period1: str | None = Field(None, description="Start time (HH:MM format)")
        discharge_end_time_period1: str | None = Field(None, description="End time (HH:MM format)")
        enable_time_period2: int = Field(0, ge=0, le=1, description="Enable second time period (0=no, 1=yes)")
        charge_start_time_period2: str | None = Field(None, description="Start time (HH:MM format)")
        charge_end_time_period2: str | None = Field(None, description="End time (HH:MM format)")
        discharge_start_time_period2: str | None = Field(None, description="Start time (HH:MM format)")
        discharge_end_time_period2: str | None = Field(None, description="End time (HH:MM format)")

    # Routes
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint (no auth required)."""
        return {"status": "ok"}

    @app.post("/api/realtime-data")
    async def get_realtime_data_endpoint(
        req: RealtimeDataRequest,
        authorization: Annotated[str, Header()] = "",
    ) -> dict:
        """Fetch real-time solar inverter data.

        Requires bearer token in Authorization header.
        """
        await verify_api_key(authorization)
        try:
            return await get_realtime_data_impl(req.device_sn)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/battery/self-use-mode")
    async def set_battery_self_use_mode_endpoint(
        req: SetBatterySelfUseModeRequest,
        authorization: Annotated[str, Header()] = "",
    ) -> dict:
        """Set inverter battery to Self Use Mode with configurable thresholds.

        Requires bearer token in Authorization header.
        """
        await verify_api_key(authorization)
        try:
            return await set_battery_self_use_mode_impl(
                device_sn=req.device_sn,
                min_soc=req.min_soc,
                charge_upper_soc=req.charge_upper_soc,
                charge_from_grid_enable=req.charge_from_grid_enable,
                charge_start_time_period1=req.charge_start_time_period1,
                charge_end_time_period1=req.charge_end_time_period1,
                discharge_start_time_period1=req.discharge_start_time_period1,
                discharge_end_time_period1=req.discharge_end_time_period1,
                enable_time_period2=req.enable_time_period2,
                charge_start_time_period2=req.charge_start_time_period2,
                charge_end_time_period2=req.charge_end_time_period2,
                discharge_start_time_period2=req.discharge_start_time_period2,
                discharge_end_time_period2=req.discharge_end_time_period2,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    return app


def main() -> None:
    """Run the HTTP server."""
    import uvicorn

    app = create_app()
    port = int(os.getenv("HTTP_PORT", "8000"))
    host = os.getenv("HTTP_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
