"""ORM models for the AI Memory Layer."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from ai_memory_layer.database import Base


USE_PGVECTOR_STUB = os.environ.get("AIML_USE_PGVECTOR_STUB") == "1"

if not USE_PGVECTOR_STUB:
    from pgvector.sqlalchemy import Vector as VectorType  # type: ignore[assignment]
else:

    class VectorType(TypeDecorator):
        """JSON-backed stub for environments where pgvector isn't available."""

        impl = JSON
        cache_ok = True

        def process_bind_param(self, value, dialect):
            return value

        def process_result_value(self, value, dialect):
            return value

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    message_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    importance_score: Mapped[float | None] = mapped_column()
    embedding: Mapped[list[float] | None] = mapped_column(VectorType(), nullable=True)
    embedding_status: Mapped[str] = mapped_column(
        Enum("pending", "completed", "failed", name="embedding_status"), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class ArchivedMessage(Base):
    __tablename__ = "archived_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    message_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    importance_score: Mapped[float | None] = mapped_column()
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archive_reason: Mapped[str] = mapped_column(String(255))


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=30)
    importance_threshold: Mapped[float] = mapped_column()
    max_items: Mapped[int | None] = mapped_column(Integer)
    delete_after_days: Mapped[int] = mapped_column(Integer, default=90)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class EmbeddingJob(Base):
    __tablename__ = "embedding_jobs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed", name="embedding_job_status"),
        default="pending",
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RetentionRule(Base):
    """Advanced retention rule model for sophisticated lifecycle management."""

    __tablename__ = "retention_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="age, importance, conversation_age, max_items, custom",
    )
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="archive, delete, move_to_cold_storage",
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_applied: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
