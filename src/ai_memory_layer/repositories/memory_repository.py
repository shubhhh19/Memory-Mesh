"""Persistence helpers for memory entities."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.models.memory import ArchivedMessage, Message, RetentionPolicy


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
            metadata=metadata,
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
                updated_at=datetime.utcnow(),
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
        importance_min: float,
        limit: int,
    ) -> Sequence[Message]:
        stmt: Select[tuple[Message]] = select(Message).where(
            Message.tenant_id == tenant_id, Message.archived.is_(False)
        )
        if conversation_id:
            stmt = stmt.where(Message.conversation_id == conversation_id)
        if importance_min:
            stmt = stmt.where(Message.importance_score >= importance_min)
        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

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
            policy.updated_at = datetime.utcnow()
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
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
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
                metadata=message.metadata,
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
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
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
