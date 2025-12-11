"""Routes for message ingestion and management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_read_session, get_session
from ai_memory_layer.models.memory import Message
from ai_memory_layer.models.user import User
from ai_memory_layer.schemas.messages import (
    MessageBatchCreate,
    MessageBatchDelete,
    MessageBatchResponse,
    MessageBatchUpdate,
    MessageCreate,
    MessageResponse,
    MessageUpdate,
)
from ai_memory_layer.security import get_current_active_user, get_tenant_id_from_user, require_api_key
from ai_memory_layer.services.message_service import MessageService
from ai_memory_layer.utils.sanitization import sanitize_metadata

router = APIRouter()
service = MessageService()


@router.post("", response_model=MessageResponse, dependencies=[Depends(require_api_key)])
async def create_message(
    payload: MessageCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Create a new message."""
    result = await service.ingest(session, payload)
    response.status_code = (
        status.HTTP_202_ACCEPTED if service.settings.async_embeddings else status.HTTP_200_OK
    )
    return result


@router.post("/batch", response_model=MessageBatchResponse, dependencies=[Depends(require_api_key)])
async def create_messages_batch(
    payload: MessageBatchCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> MessageBatchResponse:
    """Create multiple messages in a batch."""
    from ai_memory_layer.logging import get_logger
    
    logger = get_logger(component=__name__)
    created = []
    errors = []
    
    for idx, msg_data in enumerate(payload.messages):
        try:
            result = await service.ingest(session, msg_data)
            created.append(result)
        except Exception as e:
            # Log the full error internally but return sanitized message to client
            logger.exception(f"Batch create failed for message {idx}: {e}")
            errors.append({"message_index": idx, "error": "Failed to create message"})
    
    await session.commit()
    
    response.status_code = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED
    return MessageBatchResponse(created=created, updated=[], deleted=[], errors=errors)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    tenant_id: str = Query(..., description="Tenant ID for authorization"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: AsyncSession = Depends(get_read_session),
) -> MessageResponse:
    """Get a specific message."""
    try:
        message_uuid = UUID(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message id") from exc
    
    # If user is authenticated, use their tenant_id (override query param for security)
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    result = await service.fetch(session, message_uuid)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Always verify tenant access - tenant_id is now required
    if result.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return result


@router.put("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: str,
    message_update: MessageUpdate,
    tenant_id: str = Query(..., description="Tenant ID for authorization"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Update a message."""
    try:
        message_uuid = UUID(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message id") from exc
    
    # If user is authenticated, use their tenant_id (override query param for security)
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    # Get message - always filter by tenant_id for security
    stmt = select(Message).where(Message.id == message_uuid, Message.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Update fields
    update_data = message_update.model_dump(exclude_unset=True)
    
    if "content" in update_data and update_data["content"]:
        message.content = update_data["content"]
        # If content changed, we may need to regenerate embedding
        # For now, just mark as pending if async embeddings are enabled
        if service.settings.async_embeddings:
            message.embedding_status = "pending"
            await service.repository.enqueue_embedding_job(session, message.id)
    
    if "metadata" in update_data and update_data["metadata"] is not None:
        message.message_metadata = sanitize_metadata(update_data["metadata"])
    
    if "importance_override" in update_data and update_data["importance_override"] is not None:
        # Recalculate importance if content changed
        if "content" in update_data:
            from ai_memory_layer.services.importance import ImportanceScorer
            scorer = ImportanceScorer()
            message.importance_score = await scorer.score(
                role=message.role,
                content=message.content,
                explicit_importance=update_data["importance_override"],
            )
        else:
            message.importance_score = update_data["importance_override"]
    
    if "archived" in update_data and update_data["archived"] is not None:
        message.archived = update_data["archived"]
    
    await session.commit()
    await session.refresh(message)
    
    return MessageResponse.model_validate(message)


@router.post("/batch/update", response_model=MessageBatchResponse)
async def update_messages_batch(
    payload: MessageBatchUpdate,
    tenant_id: str = Query(..., description="Tenant ID for authorization"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: AsyncSession = Depends(get_session),
) -> MessageBatchResponse:
    """Update multiple messages in a batch."""
    # If user is authenticated, use their tenant_id (override query param for security)
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    # Fetch all messages in a single query - always filter by tenant_id for security
    message_ids = [update.message_id for update in payload.updates]
    stmt = select(Message).where(Message.id.in_(message_ids), Message.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    messages_dict = {msg.id: msg for msg in result.scalars().all()}
    
    updated = []
    errors = []
    
    # Track updated messages for response
    updated_messages = []
    
    for batch_update in payload.updates:
        try:
            message = messages_dict.get(batch_update.message_id)
            
            if not message:
                errors.append({"message_id": str(batch_update.message_id), "error": "Message not found"})
                continue
            
            # Apply update (similar to single update)
            update_data = batch_update.update.model_dump(exclude_unset=True)
            
            if "content" in update_data and update_data["content"]:
                message.content = update_data["content"]
                if service.settings.async_embeddings:
                    message.embedding_status = "pending"
                    await service.repository.enqueue_embedding_job(session, message.id)
            
            if "metadata" in update_data and update_data["metadata"] is not None:
                message.message_metadata = sanitize_metadata(update_data["metadata"])
            
            if "importance_override" in update_data and update_data["importance_override"] is not None:
                if "content" in update_data:
                    from ai_memory_layer.services.importance import ImportanceScorer
                    scorer = ImportanceScorer()
                    message.importance_score = await scorer.score(
                        role=message.role,
                        content=message.content,
                        explicit_importance=update_data["importance_override"],
                    )
                else:
                    message.importance_score = update_data["importance_override"]
            
            if "archived" in update_data and update_data["archived"] is not None:
                message.archived = update_data["archived"]
            
            updated_messages.append(message)
        except Exception as e:
            # Log the full error internally but return sanitized message to client
            from ai_memory_layer.logging import get_logger
            logger = get_logger(component=__name__)
            logger.exception(f"Batch update failed for message {batch_update.message_id}: {e}")
            errors.append({"message_id": str(batch_update.message_id), "error": "Failed to update message"})
    
    # Flush all changes at once for better performance
    if updated_messages:
        await session.flush()
    
    await session.commit()
    
    # Build response after commit
    updated = [MessageResponse.model_validate(msg) for msg in updated_messages]
    
    return MessageBatchResponse(created=[], updated=updated, deleted=[], errors=errors)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    tenant_id: str = Query(..., description="Tenant ID for authorization"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a message."""
    try:
        message_uuid = UUID(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message id") from exc
    
    # If user is authenticated, use their tenant_id (override query param for security)
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    # Always filter by tenant_id for security
    stmt = select(Message).where(Message.id == message_uuid, Message.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    await session.delete(message)
    await session.commit()


@router.post("/batch/delete", response_model=MessageBatchResponse)
async def delete_messages_batch(
    payload: MessageBatchDelete,
    tenant_id: str = Query(..., description="Tenant ID for authorization"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: AsyncSession = Depends(get_session),
) -> MessageBatchResponse:
    """Delete multiple messages in a batch."""
    from sqlalchemy import delete
    from ai_memory_layer.logging import get_logger
    
    logger = get_logger(component=__name__)
    
    # If user is authenticated, use their tenant_id (override query param for security)
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    # First, verify all messages belong to this tenant
    verify_stmt = select(Message.id).where(
        Message.id.in_(payload.message_ids),
        Message.tenant_id == tenant_id
    )
    result = await session.execute(verify_stmt)
    valid_ids = {row[0] for row in result.fetchall()}
    
    # Check for unauthorized access attempts
    unauthorized_ids = set(payload.message_ids) - valid_ids
    errors = []
    for msg_id in unauthorized_ids:
        errors.append({"message_id": str(msg_id), "error": "Message not found or access denied"})
    
    # Delete only the valid messages
    if valid_ids:
        stmt = delete(Message).where(
            Message.id.in_(list(valid_ids)),
            Message.tenant_id == tenant_id
        )
        
        try:
            result = await session.execute(stmt)
            deleted_count = result.rowcount or 0
            await session.commit()
            deleted = list(valid_ids)[:deleted_count]
        except Exception as e:
            await session.rollback()
            logger.exception(f"Batch delete failed: {e}")
            return MessageBatchResponse(
                created=[],
                updated=[],
                deleted=[],
                errors=[{"error": "Batch delete operation failed"}],
            )
    else:
        deleted = []
    
    return MessageBatchResponse(created=[], updated=[], deleted=deleted, errors=errors)
