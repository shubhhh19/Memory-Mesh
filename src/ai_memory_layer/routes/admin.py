"""Admin and health endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_session
from ai_memory_layer.schemas.admin import HealthResponse, RetentionRunRequest, RetentionRunResponse
from ai_memory_layer.services.retention import RetentionService

router = APIRouter()
retention_service = RetentionService()


@router.post("/retention/run", response_model=RetentionRunResponse)
async def run_retention(
    payload: RetentionRunRequest,
    session: AsyncSession = Depends(get_session),
) -> RetentionRunResponse:
    if not payload.actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="At least one action required"
        )
    result = await retention_service.run(
        session,
        tenant_id=payload.tenant_id,
        dry_run=payload.dry_run,
    )
    return RetentionRunResponse(
        archived=result.archived,
        deleted=result.deleted,
        dry_run=payload.dry_run,
    )


@router.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    status_code = "ok"
    db_status = "ok"
    notes = None
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - network/db failures
        db_status = "down"
        status_code = "degraded"
        notes = str(exc)
    return HealthResponse(
        status=status_code,
        database=db_status,  # type: ignore[arg-type]
        timestamp=datetime.now(timezone.utc),
        notes=notes,
    )
