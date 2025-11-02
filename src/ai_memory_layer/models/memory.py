"""ORM models for the AI Memory Layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ai_memory_layer.config import get_settings
from ai_memory_layer.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    importance_score: Mapped[float | None] = mapped_column()
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(get_settings().embedding_dimensions), nullable=True
    )
    embedding_status: Mapped[str] = mapped_column(
        Enum("pending", "completed", "failed", name="embedding_status"), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class ArchivedMessage(Base):
    __tablename__ = "archived_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    importance_score: Mapped[float | None] = mapped_column()
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    archive_reason: Mapped[str] = mapped_column(String(255))


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=30)
    importance_threshold: Mapped[float] = mapped_column()
    max_items: Mapped[int | None] = mapped_column(Integer)
    delete_after_days: Mapped[int] = mapped_column(Integer, default=90)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
