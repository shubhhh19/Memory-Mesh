"""Persistence helpers for memory entities."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.models.memory import ArchivedMessage, EmbeddingJob, Message, RetentionPolicy


class MemoryRepository:
    """Repository encapsulating DB access for memories."""

    async def create_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any],
    ) -> Message:
        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )
        session.add(message)
        await session.flush()
        return message

    async def update_message_embedding(
        self,
        session: AsyncSession,
        message_id: UUID,
        *,
        embedding: list[float] | None,
        importance_score: float | None,
        status: str,
    ) -> Message | None:
        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(
                embedding=embedding,
                importance_score=importance_score,
                embedding_status=status,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Message)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_message(self, session: AsyncSession, message_id: UUID) -> Message | None:
        stmt = select(Message).where(Message.id == message_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_messages(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        conversation_id: str | None,
        importance_min: float | None,
        limit: int,
    ) -> Sequence[Message]:
        stmt: Select[tuple[Message]] = select(Message).where(
            Message.tenant_id == tenant_id,
            Message.archived.is_(False),
            Message.embedding_status == "completed",
        )
        if conversation_id:
            stmt = stmt.where(Message.conversation_id == conversation_id)
        if importance_min is not None:
            stmt = stmt.where(Message.importance_score >= importance_min)
        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def search_similar_messages(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        conversation_id: str | None,
        importance_min: float | None,
        limit: int,
        query_embedding: list[float],
    ) -> Sequence[Message] | None:
        bind = session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return None
        distance = Message.embedding.l2_distance(query_embedding).label("distance")
        stmt: Select[tuple[Message]] = (
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.archived.is_(False),
                Message.embedding.is_not(None),
                Message.embedding_status == "completed",
            )
            .order_by(distance.asc())
            .limit(limit)
        )
        if conversation_id:
            stmt = stmt.where(Message.conversation_id == conversation_id)
        if importance_min is not None:
            stmt = stmt.where(Message.importance_score >= importance_min)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def enqueue_embedding_job(
        self,
        session: AsyncSession,
        message_id: UUID,
    ) -> EmbeddingJob:
        job = EmbeddingJob(message_id=message_id, status="pending")
        session.add(job)
        await session.flush()
        return job

    async def claim_embedding_jobs(
        self,
        session: AsyncSession,
        *,
        limit: int,
        max_attempts: int,
        retry_backoff_seconds: float,
    ) -> Sequence[EmbeddingJob]:
        now = datetime.now(timezone.utc)
        retry_cutoff = now - timedelta(seconds=retry_backoff_seconds)
        stmt: Select[tuple[EmbeddingJob]] = (
            select(EmbeddingJob)
            .where(
                (EmbeddingJob.status == "pending")
                | (
                    (EmbeddingJob.status == "failed")
                    & (EmbeddingJob.attempts < max_attempts)
                    & (EmbeddingJob.updated_at <= retry_cutoff)
                )
            )
            .order_by(EmbeddingJob.updated_at.asc())
            .limit(limit)
        )
        if session.bind and session.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update(skip_locked=True)
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            job.status = "running"
            job.attempts += 1
            job.updated_at = now
        await session.flush()
        return jobs

    async def get_embedding_job(self, session: AsyncSession, job_id: UUID) -> EmbeddingJob | None:
        stmt = select(EmbeddingJob).where(EmbeddingJob.id == job_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_embedding_job(
        self,
        session: AsyncSession,
        message_id: UUID | None = None,
        job_id: UUID | None = None,
        *,
        status: str,
        error: str | None = None,
    ) -> None:
        if message_id is None and job_id is None:  # pragma: no cover - guardrail
            raise ValueError("message_id or job_id is required")
        stmt = update(EmbeddingJob).values(
            status=status,
            last_error=error,
            updated_at=datetime.now(timezone.utc),
        )
        if message_id is not None:
            stmt = stmt.where(EmbeddingJob.message_id == message_id)
        if job_id is not None:
            stmt = stmt.where(EmbeddingJob.id == job_id)
        await session.execute(stmt)

    async def upsert_retention_policy(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        max_age_days: int,
        importance_threshold: float,
        max_items: int | None,
        delete_after_days: int,
    ) -> RetentionPolicy:
        stmt = select(RetentionPolicy).where(RetentionPolicy.tenant_id == tenant_id)
        result = await session.execute(stmt)
        policy = result.scalar_one_or_none()
        if policy is None:
            policy = RetentionPolicy(
                tenant_id=tenant_id,
                max_age_days=max_age_days,
                importance_threshold=importance_threshold,
                max_items=max_items,
                delete_after_days=delete_after_days,
            )
            session.add(policy)
        else:
            policy.max_age_days = max_age_days
            policy.importance_threshold = importance_threshold
            policy.max_items = max_items
            policy.delete_after_days = delete_after_days
            policy.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return policy

    async def load_policy(
        self, session: AsyncSession, tenant_id: str
    ) -> RetentionPolicy | None:
        stmt = select(RetentionPolicy).where(RetentionPolicy.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def archive_candidates(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        older_than_days: int,
        importance_threshold: float,
    ) -> Sequence[Message]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stmt = select(Message).where(
            Message.tenant_id == tenant_id,
            Message.archived.is_(False),
            (
                (Message.importance_score <= importance_threshold)
                | (Message.created_at <= cutoff)
            ),
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def move_to_archive(
        self, session: AsyncSession, *, messages: Sequence[Message], reason: str
    ) -> int:
        count = 0
        for message in messages:
            archived = ArchivedMessage(
                id=message.id,
                tenant_id=message.tenant_id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                metadata=message.message_metadata,
                importance_score=message.importance_score,
                archive_reason=reason,
            )
            session.add(archived)
            message.archived = True
            count += 1
        await session.flush()
        return count

    async def delete_archived(
        self, session: AsyncSession, *, older_than_days: int, tenant_id: str
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stmt = (
            select(ArchivedMessage)
            .where(
                ArchivedMessage.tenant_id == tenant_id,
                ArchivedMessage.archived_at <= cutoff,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        deleted = len(rows)
        for row in rows:
            await session.delete(row)
        return deleted

    async def count_messages(self, session: AsyncSession, tenant_id: str) -> int:
        stmt = select(func.count()).select_from(Message).where(Message.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one()

    async def list_tenants(self, session: AsyncSession) -> Sequence[str]:
        stmt = select(Message.tenant_id).distinct()
        result = await session.execute(stmt)
        return [row[0] for row in result.fetchall()]
