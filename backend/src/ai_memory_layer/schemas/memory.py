"""Schemas for memory retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MemorySearchParams(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    conversation_id: str | None = None
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    importance_min: float | None = Field(default=None, ge=0.0, le=1.0)
    candidate_limit: int = Field(default=200, ge=1, le=1000)


class MemorySearchResult(BaseModel):
    message_id: UUID
    score: float
    similarity: float
    decay: float
    content: str
    role: str
    metadata: dict[str, Any]
    created_at: datetime
    importance: float | None


class MemorySearchResponse(BaseModel):
    total: int
    items: list[MemorySearchResult]
