"""Schemas for message ingest and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_memory_layer.utils.sanitization import MetadataValidationError, sanitize_metadata

ALLOWED_TENANT_PATTERN = r"^[A-Za-z0-9_.-]+$"


class MessageCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64, pattern=ALLOWED_TENANT_PATTERN)
    conversation_id: str = Field(..., min_length=1, max_length=128, pattern=ALLOWED_TENANT_PATTERN)
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=100000)  # 100KB max
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    importance_override: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("metadata", mode="before")
    @classmethod
    def _sanitize_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        try:
            return sanitize_metadata(value)
        except MetadataValidationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("content")
    @classmethod
    def _trim_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be empty")
        return cleaned


class MessageUpdate(BaseModel):
    """Schema for updating a message."""

    content: str | None = Field(None, min_length=1, max_length=100000)
    metadata: dict[str, Any] | None = None
    importance_override: float | None = Field(None, ge=0.0, le=1.0)
    archived: bool | None = None

    @field_validator("metadata", mode="before")
    @classmethod
    def _sanitize_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        try:
            from ai_memory_layer.utils.sanitization import MetadataValidationError, sanitize_metadata
            return sanitize_metadata(value)
        except MetadataValidationError as exc:
            raise ValueError(str(exc)) from exc


class MessageBatchCreate(BaseModel):
    """Schema for batch message creation."""

    messages: list[MessageCreate] = Field(..., min_length=1, max_length=100)


class MessageBatchUpdateItem(BaseModel):
    """Schema for a single message update in batch."""

    message_id: UUID
    update: MessageUpdate


class MessageBatchUpdate(BaseModel):
    """Schema for batch message update."""

    updates: list[MessageBatchUpdateItem] = Field(..., min_length=1, max_length=100)


class MessageBatchDelete(BaseModel):
    """Schema for batch message deletion."""

    message_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class MessageBatchResponse(BaseModel):
    """Schema for batch operation response."""

    created: list[MessageResponse]
    updated: list[MessageResponse]
    deleted: list[UUID]
    errors: list[dict[str, Any]]


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    tenant_id: str
    conversation_id: str
    role: str
    content: str
    metadata: dict[str, Any] = Field(alias="message_metadata")
    importance_score: float | None
    embedding_status: str
    created_at: datetime
    updated_at: datetime
