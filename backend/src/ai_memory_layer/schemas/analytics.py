"""Analytics and usage statistics schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    """Schema for usage statistics."""

    tenant_id: str
    total_messages: int
    total_conversations: int
    active_conversations: int
    archived_conversations: int
    messages_today: int
    messages_this_week: int
    messages_this_month: int
    avg_importance_score: float | None
    total_embeddings: int
    pending_embeddings: int
    failed_embeddings: int


class MessageTrend(BaseModel):
    """Schema for message trend data."""

    date: str
    count: int
    role_breakdown: dict[str, int]


class ConversationActivity(BaseModel):
    """Schema for conversation activity."""

    conversation_id: str
    tenant_id: str
    message_count: int
    last_activity: datetime
    avg_importance: float | None


class EmbeddingStats(BaseModel):
    """Schema for embedding statistics."""

    total_embeddings: int
    completed: int
    pending: int
    failed: int
    avg_processing_time_seconds: float | None
    success_rate: float


class TenantUsage(BaseModel):
    """Schema for tenant usage data."""

    tenant_id: str
    total_messages: int
    total_conversations: int
    storage_size_mb: float | None
    last_activity: datetime | None


class AnalyticsResponse(BaseModel):
    """Schema for analytics response."""

    usage_stats: UsageStats | None = None
    message_trends: list[MessageTrend] = Field(default_factory=list)
    top_conversations: list[ConversationActivity] = Field(default_factory=list)
    embedding_stats: EmbeddingStats | None = None
    tenant_usage: list[TenantUsage] = Field(default_factory=list)

