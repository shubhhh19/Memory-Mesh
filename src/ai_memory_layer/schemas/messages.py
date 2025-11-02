"""Schemas for message ingest and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    conversation_id: str = Field(..., min_length=1)
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    importance_override: float | None = Field(default=None, ge=0.0, le=1.0)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: str
    conversation_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    importance_score: float | None
    embedding_status: str
    created_at: datetime
    updated_at: datetime
