"""Schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RetentionRunRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    actions: list[Literal["archive", "delete"]] = Field(default_factory=lambda: ["archive", "delete"])
    dry_run: bool = False


class RetentionRunResponse(BaseModel):
    archived: int
    deleted: int
    dry_run: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    database: Literal["ok", "down"]
    timestamp: datetime
    latency_ms: float | None = None
    uptime_seconds: float
    environment: str
    version: str
    embedding: Literal["ok", "failed"] | str = "unknown"
    notes: str | None = None
