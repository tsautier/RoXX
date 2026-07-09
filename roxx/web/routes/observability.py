"""Public service probes and Prometheus metrics routes."""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from roxx.core.observability import request_metrics
from roxx.core.readiness import collect_readiness_checks


router = APIRouter(tags=["operations"])


@router.get("/livez")
async def liveness_check() -> dict[str, str]:
    return {"status": "ok", "service": "roxx-web"}


@router.get("/readyz")
async def readiness_check() -> JSONResponse:
    checks = collect_readiness_checks()
    ready = all(checks.values())
    payload = {
        "status": "ok" if ready else "degraded",
        "service": "roxx-web",
        "checks": checks,
    }
    return JSONResponse(payload, status_code=200 if ready else 503)


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(authorization: str | None = Header(default=None)) -> str:
    expected = os.getenv("ROXX_METRICS_TOKEN")
    if expected:
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="Metrics authentication required")
    return request_metrics.render_prometheus()
