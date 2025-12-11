"""Conversation management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    conversation_id: str = Field(..., min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    tenant_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    title: str | None = Field(None, max_length=512)
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""

    title: str | None = Field(None, max_length=512)
    metadata: dict[str, Any] | None = None
    archived: bool | None = None


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: UUID | None
    title: str | None
    metadata: dict[str, Any]
    message_count: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    archived: bool


class ConversationListResponse(BaseModel):
    """Schema for conversation list response."""

    conversations: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class ConversationStats(BaseModel):
    """Schema for conversation statistics."""

    conversation_id: str
    tenant_id: str
    total_messages: int
    user_messages: int
    assistant_messages: int
    system_messages: int
    avg_importance: float | None
    first_message_at: datetime | None
    last_message_at: datetime | None

