"""High-level orchestration for message ingest and retrieval."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.config import Settings, get_settings
from ai_memory_layer.logging import get_logger
from ai_memory_layer.metrics import (
    record_embedding_job,
    record_memory_search,
    record_message_ingested,
)
from ai_memory_layer.models.memory import Message
from ai_memory_layer.repositories.memory_repository import MemoryRepository
from ai_memory_layer.schemas.messages import MessageCreate, MessageResponse
from ai_memory_layer.schemas.memory import MemorySearchParams, MemorySearchResponse, MemorySearchResult
from ai_memory_layer.services.cache import CacheService
from ai_memory_layer.services.embedding import EmbeddingService, build_embedding_service
from ai_memory_layer.services.importance import ImportanceScorer
from ai_memory_layer.services.retrieval import MemoryRetriever, default_retriever

logger = get_logger(component="message_service")


@dataclass
class MessageService:
    repository: MemoryRepository = field(default_factory=MemoryRepository)
    embedder: EmbeddingService = field(default_factory=build_embedding_service)
    scorer: ImportanceScorer = field(default_factory=ImportanceScorer)
    retriever: MemoryRetriever = field(default_factory=default_retriever)
    cache: CacheService = field(default_factory=CacheService)
    settings: Settings = field(default_factory=get_settings)

    async def ingest(
        self, session: AsyncSession, payload: MessageCreate
    ) -> MessageResponse:
        message = await self.repository.create_message(
            session,
            tenant_id=payload.tenant_id,
            conversation_id=payload.conversation_id,
            role=payload.role,
            content=payload.content,
            metadata=payload.metadata or {},
        )
        if self.settings.async_embeddings:
            await self.repository.enqueue_embedding_job(session, message.id)
            await session.commit()
            record_message_ingested(
                tenant_id=payload.tenant_id,
                role=payload.role,
                async_mode=True,
                status="queued",
            )
            return MessageResponse.model_validate(message)

        message = await self._apply_embedding(
            session,
            message=message,
            content=payload.content,
            explicit_importance=payload.importance_override,
        )
        await session.commit()
        record_message_ingested(
            tenant_id=payload.tenant_id,
            role=payload.role,
            async_mode=False,
            status=getattr(message, "embedding_status", "completed"),
        )
        return MessageResponse.model_validate(message)

    async def retrieve(
        self,
        session: AsyncSession,
        params: MemorySearchParams,
    ) -> MemorySearchResponse:
        start = time.perf_counter()
        cache_hit = False
        cache_key = None
        if self.cache.enabled:
            cache_key = self.cache.search_key(
                tenant_id=params.tenant_id,
                conversation_id=params.conversation_id,
                query=params.query,
                top_k=params.top_k,
                candidate_limit=params.candidate_limit,
            )
            cached = await self.cache.get(cache_key)
            if cached:
                cache_hit = True
                response = MemorySearchResponse.model_validate(cached)
                record_memory_search(
                    tenant_id=params.tenant_id,
                    result_count=len(response.items),
                    cached=True,
                    duration=time.perf_counter() - start,
                )
                return response

        query_embedding = await self._embed_text(params.query)
        candidate_limit = min(params.candidate_limit, self.settings.max_results * 10)
        top_k = min(params.top_k, self.settings.max_results)
        candidates = await self.repository.search_similar_messages(
            session,
            tenant_id=params.tenant_id,
            conversation_id=params.conversation_id,
            importance_min=params.importance_min,
            limit=candidate_limit,
            query_embedding=query_embedding,
        )
        if candidates is None:
            candidates = await self.repository.list_active_messages(
                session,
                tenant_id=params.tenant_id,
                conversation_id=params.conversation_id,
                importance_min=params.importance_min,
                limit=candidate_limit,
            )
        ranked = self.retriever.rank(
            query_embedding=query_embedding,
            candidates=candidates,
            top_k=top_k,
        )
        results = [
            MemorySearchResult(
                message_id=item.message.id,
                score=item.score,
                similarity=item.similarity,
                decay=item.decay,
                content=item.message.content,
                role=item.message.role,
                metadata=item.message.message_metadata,
                created_at=item.message.created_at,
                importance=item.message.importance_score,
            )
            for item in ranked
        ]
        response = MemorySearchResponse(
            total=len(results),
            items=results,
        )
        if cache_key:
            await self.cache.set(cache_key, response.model_dump(mode='json'))
        record_memory_search(
            tenant_id=params.tenant_id,
            result_count=len(results),
            cached=cache_hit,
            duration=time.perf_counter() - start,
        )
        return response

    async def fetch(self, session: AsyncSession, message_id: UUID) -> MessageResponse | None:
        message = await self.repository.get_message(session, message_id)
        if message is None:
            return None
        return MessageResponse.model_validate(message)

    async def _apply_embedding(
        self,
        session: AsyncSession,
        *,
        message: Message,
        content: str,
        explicit_importance: Optional[float],
    ):
        base_importance = explicit_importance
        if base_importance is None:
            base_importance = self.scorer.score(
                created_at=message.created_at,
                role=message.role,
                explicit_importance=None,
            )
        else:
            base_importance = max(0.0, min(base_importance, 1.0))

        start = time.perf_counter()
        try:
            embedding = await self._embed_text(content)
            status = "completed"
            error = None
        except Exception as exc:
            logger.exception("embedding_failed", message_id=str(message.id))
            embedding = None
            status = "failed"
            error = str(exc)

        updated = await self.repository.update_message_embedding(
            session,
            message.id,
            embedding=embedding,
            importance_score=base_importance,
            status=status,
        )
        record_embedding_job(status=status, duration=time.perf_counter() - start)
        if self.settings.async_embeddings:
            await self.repository.update_embedding_job(
                session, message.id, status=status, error=error
            )
        await self.cache.invalidate_search(message.tenant_id, message.conversation_id)
        return updated or message

    async def _embed_text(self, text: str) -> list[float]:
        cache_key = None
        if self.cache.enabled:
            cache_key = self.cache.embedding_key(text)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
        embedding = await self.embedder.embed(text)
        if cache_key:
            await self.cache.set(cache_key, embedding, ttl=self.cache.embedding_ttl)
        return embedding
