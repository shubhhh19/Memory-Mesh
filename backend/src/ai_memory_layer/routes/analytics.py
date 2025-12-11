"""Analytics and usage statistics routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_read_session
from ai_memory_layer.models.memory import EmbeddingJob, Message
from ai_memory_layer.models.user import Conversation, User
from ai_memory_layer.schemas.analytics import (
    AnalyticsResponse,
    ConversationActivity,
    EmbeddingStats,
    MessageTrend,
    TenantUsage,
    UsageStats,
)
from ai_memory_layer.security import get_current_active_user, get_tenant_id_from_user, require_admin

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> UsageStats:
    """Get usage statistics for a tenant."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Combined query for message counts using conditional aggregation
    msg_stats_stmt = select(
        func.count(Message.id).label("total"),
        func.count().filter(Message.created_at >= today_start).label("today"),
        func.count().filter(Message.created_at >= week_start).label("week"),
        func.count().filter(Message.created_at >= month_start).label("month"),
        func.avg(Message.importance_score).label("avg_importance"),
        func.count().filter(Message.embedding.isnot(None)).label("total_embeddings"),
        func.count().filter(Message.embedding_status == "pending").label("pending_embeddings"),
        func.count().filter(Message.embedding_status == "failed").label("failed_embeddings"),
    ).where(Message.tenant_id == tenant_id)
    
    msg_stats_result = await session.execute(msg_stats_stmt)
    msg_stats = msg_stats_result.first()
    
    total_messages = msg_stats.total or 0
    messages_today = msg_stats.today or 0
    messages_this_week = msg_stats.week or 0
    messages_this_month = msg_stats.month or 0
    avg_importance = msg_stats.avg_importance
    total_embeddings = msg_stats.total_embeddings or 0
    pending_embeddings = msg_stats.pending_embeddings or 0
    failed_embeddings = msg_stats.failed_embeddings or 0
    
    # Combined query for conversation counts
    conv_stats_stmt = select(
        func.count(Conversation.id).label("total"),
        func.count().filter(Conversation.archived == False).label("active"),  # noqa: E712
        func.count().filter(Conversation.archived == True).label("archived"),  # noqa: E712
    ).where(Conversation.tenant_id == tenant_id)
    
    conv_stats_result = await session.execute(conv_stats_stmt)
    conv_stats = conv_stats_result.first()
    
    total_conversations = conv_stats.total or 0
    active_conversations = conv_stats.active or 0
    archived_conversations = conv_stats.archived or 0
    
    return UsageStats(
        tenant_id=tenant_id,
        total_messages=total_messages,
        total_conversations=total_conversations,
        active_conversations=active_conversations,
        archived_conversations=archived_conversations,
        messages_today=messages_today,
        messages_this_week=messages_this_week,
        messages_this_month=messages_this_month,
        avg_importance_score=float(avg_importance) if avg_importance else None,
        total_embeddings=total_embeddings,
        pending_embeddings=pending_embeddings,
        failed_embeddings=failed_embeddings,
    )


@router.get("/trends", response_model=list[MessageTrend])
async def get_message_trends(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> list[MessageTrend]:
    """Get message trends over time."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get messages grouped by date and role
    stmt = select(
        func.date(Message.created_at).label("date"),
        Message.role,
        func.count(Message.id).label("count"),
    ).where(
        Message.tenant_id == tenant_id,
        Message.created_at >= start_date,
    ).group_by(
        func.date(Message.created_at),
        Message.role,
    ).order_by(func.date(Message.created_at))
    
    result = await session.execute(stmt)
    rows = result.all()
    
    # Group by date
    trends_dict: dict[str, dict[str, int]] = {}
    for row in rows:
        date_str = str(row.date)
        if date_str not in trends_dict:
            trends_dict[date_str] = {}
        trends_dict[date_str][row.role] = row.count
    
    # Convert to list
    trends = []
    for date_str, role_breakdown in trends_dict.items():
        trends.append(MessageTrend(date=date_str, count=sum(role_breakdown.values()), role_breakdown=role_breakdown))
    
    return trends


@router.get("/top-conversations", response_model=list[ConversationActivity])
async def get_top_conversations(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of conversations"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> list[ConversationActivity]:
    """Get top conversations by activity."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    # Get conversations with message counts and last activity
    stmt = select(
        Conversation.id,
        Conversation.tenant_id,
        func.count(Message.id).label("message_count"),
        func.max(Message.created_at).label("last_activity"),
        func.avg(Message.importance_score).label("avg_importance"),
    ).join(
        Message,
        (Message.conversation_id == Conversation.id) & (Message.tenant_id == Conversation.tenant_id),
        isouter=True,
    ).where(
        Conversation.tenant_id == tenant_id,
    ).group_by(
        Conversation.id,
        Conversation.tenant_id,
    ).order_by(
        func.max(Message.created_at).desc(),
    ).limit(limit)
    
    result = await session.execute(stmt)
    rows = result.all()
    
    activities = []
    for row in rows:
        activities.append(
            ConversationActivity(
                conversation_id=row.id,
                tenant_id=row.tenant_id,
                message_count=row.message_count or 0,
                last_activity=row.last_activity or datetime.now(timezone.utc),
                avg_importance=float(row.avg_importance) if row.avg_importance else None,
            )
        )
    
    return activities


@router.get("/embeddings", response_model=EmbeddingStats)
async def get_embedding_stats(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> EmbeddingStats:
    """Get embedding processing statistics."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    # Count by status
    total_stmt = select(func.count(Message.id)).where(
        Message.tenant_id == tenant_id,
    )
    total_result = await session.execute(total_stmt)
    total = total_result.scalar() or 0
    
    completed_stmt = select(func.count(Message.id)).where(
        Message.tenant_id == tenant_id,
        Message.embedding_status == "completed",
    )
    completed_result = await session.execute(completed_stmt)
    completed = completed_result.scalar() or 0
    
    pending_stmt = select(func.count(Message.id)).where(
        Message.tenant_id == tenant_id,
        Message.embedding_status == "pending",
    )
    pending_result = await session.execute(pending_stmt)
    pending = pending_result.scalar() or 0
    
    failed_stmt = select(func.count(Message.id)).where(
        Message.tenant_id == tenant_id,
        Message.embedding_status == "failed",
    )
    failed_result = await session.execute(failed_stmt)
    failed = failed_result.scalar() or 0
    
    # Calculate success rate
    processed = completed + failed
    success_rate = (completed / processed * 100) if processed > 0 else 0.0
    
    return EmbeddingStats(
        total_embeddings=total,
        completed=completed,
        pending=pending,
        failed=failed,
        avg_processing_time_seconds=None,  # Would need job tracking for this
        success_rate=success_rate,
    )


@router.get("/tenants", response_model=list[TenantUsage])
async def get_tenant_usage(
    current_user: Annotated[User, Depends(require_admin)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> list[TenantUsage]:
    """Get usage statistics for all tenants (admin only)."""
    # Single query with GROUP BY to get all tenant stats at once
    msg_stats_stmt = select(
        Message.tenant_id,
        func.count(Message.id).label("total_messages"),
        func.max(Message.created_at).label("last_activity"),
    ).group_by(Message.tenant_id)
    
    msg_result = await session.execute(msg_stats_stmt)
    msg_stats = {row.tenant_id: {"messages": row.total_messages, "last_activity": row.last_activity} for row in msg_result.all()}
    
    # Get conversation counts per tenant
    conv_stats_stmt = select(
        Conversation.tenant_id,
        func.count(Conversation.id).label("total_conversations"),
    ).group_by(Conversation.tenant_id)
    
    conv_result = await session.execute(conv_stats_stmt)
    conv_stats = {row.tenant_id: row.total_conversations for row in conv_result.all()}
    
    # Combine results
    all_tenant_ids = set(msg_stats.keys()) | set(conv_stats.keys())
    usages = []
    
    for tid in all_tenant_ids:
        usages.append(
            TenantUsage(
                tenant_id=tid,
                total_messages=msg_stats.get(tid, {}).get("messages", 0) or 0,
                total_conversations=conv_stats.get(tid, 0) or 0,
                storage_size_mb=None,  # Would need to calculate from actual storage
                last_activity=msg_stats.get(tid, {}).get("last_activity"),
            )
        )
    
    return usages

