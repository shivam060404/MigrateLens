"""Minimal public process health. No tenant data or dependency credentials are exposed."""

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.domain.models import Strict

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(Strict):
    status: Literal["ok"] = "ok"
    service: Literal["migratelens-control"] = "migratelens-control"
    mode: Literal["local-reference"] = "local-reference"


class ReadinessResponse(Strict):
    status: Literal["not_ready"] = "not_ready"
    reason: Literal["Local reference and pilot acceptance gates are incomplete."] = (
        "Local reference and pilot acceptance gates are incomplete."
    )


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse, status_code=503)
def ready() -> JSONResponse:
    return JSONResponse(status_code=503, content=ReadinessResponse().model_dump())
