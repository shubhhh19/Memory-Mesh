"""Routes for message ingestion."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_session
from ai_memory_layer.schemas.messages import MessageCreate, MessageResponse
from ai_memory_layer.services.message_service import MessageService

router = APIRouter()
service = MessageService()


@router.post("", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_message(
    payload: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    return await service.ingest(session, payload)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        message_uuid = UUID(message_id)
    except ValueError as exc:  # pragma: no cover - FastAPI validation handles normally
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message id") from exc
    result = await service.fetch(session, message_uuid)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return result
