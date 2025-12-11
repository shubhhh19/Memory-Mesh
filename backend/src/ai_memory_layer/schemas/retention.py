"""Retention policy schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RetentionRuleCreate(BaseModel):
    """Schema for creating a retention rule."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    rule_type: Literal["age", "importance", "conversation_age", "max_items", "custom"] = Field(
        ..., description="Type of retention rule"
    )
    conditions: dict[str, Any] = Field(
        ..., description="Rule-specific conditions (e.g., {'days': 30, 'importance_threshold': 0.3})"
    )
    action: Literal["archive", "delete", "move_to_cold_storage"] = Field(
        ..., description="Action to take when rule matches"
    )
    priority: int = Field(default=100, ge=1, le=1000, description="Rule priority (lower = higher priority)")
    enabled: bool = Field(default=True)


class RetentionRuleUpdate(BaseModel):
    """Schema for updating a retention rule."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    conditions: dict[str, Any] | None = None
    action: Literal["archive", "delete", "move_to_cold_storage"] | None = None
    priority: int | None = Field(None, ge=1, le=1000)
    enabled: bool | None = None


class RetentionRuleResponse(BaseModel):
    """Schema for retention rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    name: str
    description: str | None
    rule_type: str
    conditions: dict[str, Any]
    action: str
    priority: int
    enabled: bool
    last_applied: datetime | None
    created_at: datetime
    updated_at: datetime


class RetentionPolicyResponse(BaseModel):
    """Schema for retention policy response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    max_age_days: int
    importance_threshold: float
    max_items: int | None
    delete_after_days: int
    created_at: datetime
    updated_at: datetime


class RetentionPolicyUpdate(BaseModel):
    """Schema for updating retention policy."""

    max_age_days: int | None = Field(None, ge=1, le=3650)
    importance_threshold: float | None = Field(None, ge=0.0, le=1.0)
    max_items: int | None = Field(None, ge=1)
    delete_after_days: int | None = Field(None, ge=1, le=3650)


class RetentionExecutionResponse(BaseModel):
    """Schema for retention execution result."""

    tenant_id: str
    rules_applied: list[str]
    messages_archived: int
    messages_deleted: int
    messages_moved_to_cold: int
    execution_time_seconds: float
    dry_run: bool

