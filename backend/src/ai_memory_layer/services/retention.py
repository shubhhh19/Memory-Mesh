"""Retention and archival workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.config import get_settings
from ai_memory_layer.repositories.memory_repository import MemoryRepository


@dataclass
class RetentionResult:
    archived: int
    deleted: int


class RetentionService:
    """Applies tenant retention policies for archiving and deletion."""

    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    async def run(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        actions: set[str] | None = None,
        dry_run: bool = False,
    ) -> RetentionResult:
        actions = actions or {"archive", "delete"}
        settings = get_settings()
        policy = await self.repository.load_policy(session, tenant_id)
        if policy is None:
            policy = await self.repository.upsert_retention_policy(
                session,
                tenant_id=tenant_id,
                max_age_days=settings.retention_max_age_days,
                importance_threshold=settings.retention_importance_threshold,
                max_items=None,
                delete_after_days=settings.retention_delete_after_days,
            )

        candidates = await self.repository.archive_candidates(
            session,
            tenant_id=tenant_id,
            older_than_days=policy.max_age_days,
            importance_threshold=policy.importance_threshold,
        )

        archived = 0
        deleted = 0
        if not dry_run and candidates and "archive" in actions:
            archived = await self.repository.move_to_archive(
                session, messages=candidates, reason="policy"
            )
        if not dry_run and "delete" in actions:
            deleted = await self.repository.delete_archived(
                session,
                older_than_days=policy.delete_after_days,
                tenant_id=tenant_id,
            )
        await session.commit()
        return RetentionResult(
            archived=archived if (not dry_run and "archive" in actions) else 0,
            deleted=deleted if (not dry_run and "delete" in actions) else 0,
        )
