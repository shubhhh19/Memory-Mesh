"""Admin and health endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_session
from ai_memory_layer.schemas.admin import HealthResponse, RetentionRunRequest, RetentionRunResponse
from ai_memory_layer.security import require_api_key
from ai_memory_layer.services.health import HealthService
from ai_memory_layer.services.retention import RetentionService
from ai_memory_layer.services.health import HealthReport

router = APIRouter()
retention_service = RetentionService()


@router.post("/retention/run", response_model=RetentionRunResponse)
async def run_retention(
    payload: RetentionRunRequest,
    session: AsyncSession = Depends(get_session),
    _: str | None = Depends(require_api_key),
) -> RetentionRunResponse:
    if not payload.actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="At least one action required"
        )
    result = await retention_service.run(
        session,
        tenant_id=payload.tenant_id,
        actions=set(payload.actions),
        dry_run=payload.dry_run,
    )
    return RetentionRunResponse(
        archived=result.archived,
        deleted=result.deleted,
        dry_run=payload.dry_run,
    )


def _build_response(report: HealthReport) -> HealthResponse:
    return HealthResponse(
        status=report.status,
        database=report.database,  # type: ignore[arg-type]
        timestamp=report.timestamp,
        latency_ms=report.latency_ms,
        uptime_seconds=report.uptime_seconds,
        environment=report.environment,
        version=report.version,
        embedding=report.embedding,
        notes=report.notes,
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    start_time = getattr(request.app.state, "start_time", datetime.now(timezone.utc))
    service = HealthService(start_time=start_time)
    report = await service.build_liveness()
    return _build_response(report)


@router.get("/readiness", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    start_time = getattr(request.app.state, "start_time", datetime.now(timezone.utc))
    service = HealthService(start_time=start_time)
    report = await service.build_readiness()
    return _build_response(report)
