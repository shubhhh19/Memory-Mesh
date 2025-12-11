"""Routes for memory retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_read_session
from ai_memory_layer.schemas.memory import MemorySearchParams, MemorySearchResponse
from ai_memory_layer.security import require_api_key
from ai_memory_layer.services.message_service import MessageService

router = APIRouter(dependencies=[Depends(require_api_key)])
service = MessageService()


@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    tenant_id: str,
    query: str,
    conversation_id: str | None = None,
    top_k: int = 5,
    importance_min: float | None = None,
    candidate_limit: int = 200,
    session: AsyncSession = Depends(get_read_session),
) -> MemorySearchResponse:
    params = MemorySearchParams(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        query=query,
        top_k=top_k,
        importance_min=importance_min,
        candidate_limit=candidate_limit,
    )
    return await service.retrieve(session, params)
