"""Conversation management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_read_session, get_session
from ai_memory_layer.models.memory import Message
from ai_memory_layer.models.user import Conversation, User
from ai_memory_layer.schemas.conversations import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationStats,
    ConversationUpdate,
)
from ai_memory_layer.security import get_current_active_user, get_tenant_id_from_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationResponse:
    """Create a new conversation."""
    # Use tenant_id from user if available, otherwise from request
    tenant_id = get_tenant_id_from_user(current_user) or conversation_data.tenant_id
    
    # Check if conversation already exists
    stmt = select(Conversation).where(
        Conversation.id == conversation_data.conversation_id,
        Conversation.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        return ConversationResponse.model_validate(existing)
    
    conversation = Conversation(
        id=conversation_data.conversation_id,
        tenant_id=tenant_id,
        user_id=current_user.id,
        title=conversation_data.title,
        metadata=conversation_data.metadata or {},
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    archived: bool | None = Query(None, description="Filter by archived status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> ConversationListResponse:
    """List conversations with pagination."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    # Build query
    stmt = select(Conversation).where(Conversation.tenant_id == tenant_id)
    
    if current_user:
        stmt = stmt.where(Conversation.user_id == current_user.id)
    
    if archived is not None:
        stmt = stmt.where(Conversation.archived == archived)
    
    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Paginate
    stmt = stmt.order_by(Conversation.updated_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(stmt)
    conversations = result.scalars().all()
    
    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> ConversationResponse:
    """Get a specific conversation."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
    )
    
    if current_user:
        stmt = stmt.where(Conversation.user_id == current_user.id)
    
    result = await session.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    return ConversationResponse.model_validate(conversation)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> ConversationResponse:
    """Update a conversation."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
    )
    
    if current_user:
        stmt = stmt.where(Conversation.user_id == current_user.id)
    
    result = await session.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # Update fields
    update_data = conversation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(conversation, key, value)
    
    await session.commit()
    await session.refresh(conversation)
    
    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    delete_messages: bool = Query(False, description="Also delete associated messages"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> None:
    """Delete a conversation."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
    )
    
    if current_user:
        stmt = stmt.where(Conversation.user_id == current_user.id)
    
    result = await session.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # Delete associated messages if requested
    if delete_messages:
        msg_stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,
        )
        msg_result = await session.execute(msg_stmt)
        messages = msg_result.scalars().all()
        for msg in messages:
            await session.delete(msg)
    
    await session.delete(conversation)
    await session.commit()


@router.get("/{conversation_id}/stats", response_model=ConversationStats)
async def get_conversation_stats(
    conversation_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> ConversationStats:
    """Get statistics for a conversation."""
    # Use tenant_id from user if available
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    # Get message counts by role
    stmt = select(
        func.count(Message.id).label("total"),
        func.count().filter(Message.role == "user").label("user_count"),
        func.count().filter(Message.role == "assistant").label("assistant_count"),
        func.count().filter(Message.role == "system").label("system_count"),
        func.avg(Message.importance_score).label("avg_importance"),
        func.min(Message.created_at).label("first_message"),
        func.max(Message.created_at).label("last_message"),
    ).where(
        Message.conversation_id == conversation_id,
        Message.tenant_id == tenant_id,
    )
    
    result = await session.execute(stmt)
    stats = result.first()
    
    if not stats or stats.total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No messages found for this conversation",
        )
    
    return ConversationStats(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        total_messages=stats.total or 0,
        user_messages=stats.user_count or 0,
        assistant_messages=stats.assistant_count or 0,
        system_messages=stats.system_count or 0,
        avg_importance=float(stats.avg_importance) if stats.avg_importance else None,
        first_message_at=stats.first_message,
        last_message_at=stats.last_message,
    )

