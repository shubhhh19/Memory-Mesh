"""High-level orchestration for message ingest and retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.repositories.memory_repository import MemoryRepository
from ai_memory_layer.schemas.messages import MessageCreate, MessageResponse
from ai_memory_layer.schemas.memory import MemorySearchResponse, MemorySearchResult
from ai_memory_layer.schemas.memory import MemorySearchParams
from ai_memory_layer.services.embedding import EmbeddingService, build_embedding_service
from ai_memory_layer.services.importance import ImportanceScorer
from ai_memory_layer.services.retrieval import MemoryRetriever, default_retriever


@dataclass
class MessageService:
    repository: MemoryRepository = MemoryRepository()
    embedder: EmbeddingService = build_embedding_service()
    scorer: ImportanceScorer = ImportanceScorer()
    retriever: MemoryRetriever = default_retriever()

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
        importance = payload.importance_override
        if importance is None:
            importance = self.scorer.score(
                created_at=message.created_at,
                role=message.role,
                explicit_importance=payload.importance_override,
            )
        embedding = await self.embedder.embed(payload.content)
        message = await self.repository.update_message_embedding(
            session,
            message.id,
            embedding=embedding,
            importance_score=importance,
            status="completed",
        )
        await session.commit()
        assert message is not None
        return MessageResponse.from_orm(message)

    async def retrieve(
        self,
        session: AsyncSession,
        params: MemorySearchParams,
    ) -> MemorySearchResponse:
        query_embedding = await self.embedder.embed(params.query)
        candidates = await self.repository.list_active_messages(
            session,
            tenant_id=params.tenant_id,
            conversation_id=params.conversation_id,
            importance_min=params.importance_min,
            limit=params.candidate_limit,
        )
        ranked = self.retriever.rank(
            query_embedding=query_embedding,
            candidates=candidates,
            top_k=params.top_k,
        )
        results = [
            MemorySearchResult(
                message_id=item.message.id,
                score=item.score,
                similarity=item.similarity,
                decay=item.decay,
                content=item.message.content,
                role=item.message.role,
                metadata=item.message.metadata,
                created_at=item.message.created_at,
                importance=item.message.importance_score,
            )
            for item in ranked
        ]
        return MemorySearchResponse(
            total=len(results),
            items=results,
        )

    async def fetch(self, session: AsyncSession, message_id: UUID) -> MessageResponse | None:
        message = await self.repository.get_message(session, message_id)
        if message is None:
            return None
        return MessageResponse.from_orm(message)
