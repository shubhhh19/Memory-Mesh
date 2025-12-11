"""Advanced retention service with sophisticated lifecycle management."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.logging import get_logger
from ai_memory_layer.models.memory import ArchivedMessage, Message, RetentionRule
from ai_memory_layer.models.user import Conversation

logger = get_logger(component="advanced_retention")


class AdvancedRetentionService:
    """Advanced retention service with rule-based lifecycle management."""

    async def apply_retention_rules(
        self,
        session: AsyncSession,
        tenant_id: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Apply all enabled retention rules for a tenant."""
        start_time = time.perf_counter()
        
        # Get all enabled rules for tenant, ordered by priority
        stmt = (
            select(RetentionRule)
            .where(
                RetentionRule.tenant_id == tenant_id,
                RetentionRule.enabled == True,  # noqa: E712
            )
            .order_by(RetentionRule.priority.asc())
        )
        result = await session.execute(stmt)
        rules = result.scalars().all()
        
        if not rules:
            return {
                "tenant_id": tenant_id,
                "rules_applied": [],
                "messages_archived": 0,
                "messages_deleted": 0,
                "messages_moved_to_cold": 0,
                "execution_time_seconds": time.perf_counter() - start_time,
                "dry_run": dry_run,
            }
        
        rules_applied = []
        messages_archived = 0
        messages_deleted = 0
        messages_moved_to_cold = 0
        
        for rule in rules:
            try:
                result = await self._apply_rule(session, rule, tenant_id, dry_run)
                rules_applied.append(rule.name)
                messages_archived += result.get("archived", 0)
                messages_deleted += result.get("deleted", 0)
                messages_moved_to_cold += result.get("moved_to_cold", 0)
                
                if not dry_run:
                    rule.last_applied = datetime.now(timezone.utc)
                    await session.flush()
            except Exception as e:
                logger.error(
                    "retention_rule_failed",
                    rule_id=rule.id,
                    rule_name=rule.name,
                    error=str(e),
                )
        
        if not dry_run:
            await session.commit()
        
        return {
            "tenant_id": tenant_id,
            "rules_applied": rules_applied,
            "messages_archived": messages_archived,
            "messages_deleted": messages_deleted,
            "messages_moved_to_cold": messages_moved_to_cold,
            "execution_time_seconds": time.perf_counter() - start_time,
            "dry_run": dry_run,
        }

    async def _apply_rule(
        self,
        session: AsyncSession,
        rule: RetentionRule,
        tenant_id: str,
        dry_run: bool,
    ) -> dict[str, int]:
        """Apply a single retention rule."""
        conditions = rule.conditions
        action = rule.action
        
        # Build query based on rule type
        stmt = select(Message).where(
            Message.tenant_id == tenant_id,
            Message.archived == False,  # noqa: E712
        )
        
        if rule.rule_type == "age":
            days = conditions.get("days", 30)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(Message.created_at <= cutoff)
        
        elif rule.rule_type == "importance":
            threshold = conditions.get("importance_threshold", 0.3)
            stmt = stmt.where(
                or_(
                    Message.importance_score <= threshold,
                    Message.importance_score.is_(None),
                )
            )
        
        elif rule.rule_type == "conversation_age":
            days = conditions.get("days", 90)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            # Get conversations with no recent activity
            conv_stmt = (
                select(Conversation.id)
                .where(
                    Conversation.tenant_id == tenant_id,
                    or_(
                        Conversation.last_message_at <= cutoff,
                        Conversation.last_message_at.is_(None),
                    ),
                )
            )
            conv_result = await session.execute(conv_stmt)
            inactive_conversation_ids = [row[0] for row in conv_result.all()]
            if inactive_conversation_ids:
                stmt = stmt.where(Message.conversation_id.in_(inactive_conversation_ids))
            else:
                return {"archived": 0, "deleted": 0, "moved_to_cold": 0}
        
        elif rule.rule_type == "max_items":
            max_items = conditions.get("max_items", 1000)
            # Get total count
            count_stmt = select(func.count(Message.id)).where(
                Message.tenant_id == tenant_id,
                Message.archived == False,  # noqa: E712
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0
            
            if total > max_items:
                # Get oldest messages beyond limit
                stmt = (
                    stmt.order_by(Message.created_at.asc())
                    .limit(total - max_items)
                )
            else:
                return {"archived": 0, "deleted": 0, "moved_to_cold": 0}
        
        elif rule.rule_type == "custom":
            # Custom rules can have complex conditions
            # Strictly validate and allow-list filter keys to prevent injection
            allowed_filters = {"role", "min_importance", "max_importance"}
            if "filters" in conditions:
                filters = conditions["filters"]
                if not isinstance(filters, dict):
                    return {"archived": 0, "deleted": 0, "moved_to_cold": 0}
                
                # Only process allowed filter keys
                for key in allowed_filters:
                    if key in filters:
                        value = filters[key]
                        if key == "role":
                            # Validate role is a string
                            if isinstance(value, str) and value in ("user", "assistant", "system"):
                                stmt = stmt.where(Message.role == value)
                        elif key == "min_importance":
                            # Validate and cast to float
                            try:
                                min_val = float(value)
                                if 0.0 <= min_val <= 1.0:
                                    stmt = stmt.where(Message.importance_score >= min_val)
                            except (ValueError, TypeError):
                                pass
                        elif key == "max_importance":
                            # Validate and cast to float
                            try:
                                max_val = float(value)
                                if 0.0 <= max_val <= 1.0:
                                    stmt = stmt.where(Message.importance_score <= max_val)
                            except (ValueError, TypeError):
                                pass
        
        # Execute query
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        if not messages:
            return {"archived": 0, "deleted": 0, "moved_to_cold": 0}
        
        # Apply action
        if action == "archive":
            if not dry_run:
                archived_count = await self._archive_messages(session, messages, rule.name)
            else:
                archived_count = len(messages)
            return {"archived": archived_count, "deleted": 0, "moved_to_cold": 0}
        
        elif action == "delete":
            if not dry_run:
                deleted_count = await self._delete_messages(session, messages)
            else:
                deleted_count = len(messages)
            return {"archived": 0, "deleted": deleted_count, "moved_to_cold": 0}
        
        elif action == "move_to_cold_storage":
            # For now, treat as archive (cold storage would require external storage)
            if not dry_run:
                archived_count = await self._archive_messages(session, messages, f"cold_storage:{rule.name}")
            else:
                archived_count = len(messages)
            return {"archived": 0, "deleted": 0, "moved_to_cold": archived_count}
        
        return {"archived": 0, "deleted": 0, "moved_to_cold": 0}

    async def _archive_messages(
        self,
        session: AsyncSession,
        messages: list[Message],
        reason: str,
    ) -> int:
        """Archive messages."""
        if not messages:
            return 0
        
        # Fetch all existing archived message IDs in a single query to avoid N+1
        message_ids = [msg.id for msg in messages]
        archived_stmt = select(ArchivedMessage.id).where(ArchivedMessage.id.in_(message_ids))
        archived_result = await session.execute(archived_stmt)
        already_archived_ids = {row[0] for row in archived_result.all()}
        
        count = 0
        for message in messages:
            # Skip if already archived
            if message.id in already_archived_ids:
                continue
            
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

    async def _delete_messages(
        self,
        session: AsyncSession,
        messages: list[Message],
    ) -> int:
        """Delete messages permanently."""
        count = 0
        for message in messages:
            await session.delete(message)
            count += 1
        
        await session.flush()
        return count

