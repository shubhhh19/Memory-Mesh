from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from httpx import AsyncClient

from ai_memory_layer.repositories.memory_repository import MemoryRepository
from ai_memory_layer.services.job_queue import EmbeddingJobQueue
from ai_memory_layer.services.message_service import MessageService


@pytest.mark.asyncio
async def test_create_and_search_message(client: AsyncClient):
    payload = {
        "tenant_id": "tenant-a",
        "conversation_id": "conv-1",
        "role": "user",
        "content": "How do I reset my password?",
        "metadata": {"channel": "web"},
    }
    response = await client.post("/v1/messages", json=payload)
    assert response.status_code == 200
    message_id = response.json()["id"]
    assert "x-request-id" in response.headers

    get_response = await client.get(f"/v1/messages/{message_id}")
    assert get_response.status_code == 200

    search_response = await client.get(
        "/v1/memory/search",
        params={"tenant_id": "tenant-a", "query": "password reset", "top_k": 3},
    )
    assert search_response.status_code == 200
    data = search_response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_async_embedding_job_queue_processes(
    test_session,
    client_builder,
    settings_override,
):
    settings_override(async_embeddings=True)
    repo = MemoryRepository()
    service = MessageService(repository=repo)

    @asynccontextmanager
    async def _session_provider():
        yield test_session

    async with client_builder() as client:
        payload = {
            "tenant_id": "async-tenant",
            "conversation_id": "c-async",
            "role": "user",
            "content": "embed this message",
        }
        response = await client.post("/v1/messages", json=payload)
        assert response.status_code == 202
        message_id = UUID(response.json()["id"])

        message = await repo.get_message(test_session, message_id)
        assert message is not None
        assert message.embedding_status == "pending"

        queue = EmbeddingJobQueue(
            repository=repo,
            service=service,
            session_provider=_session_provider,
        )
        processed = await queue.drain_once()
        assert processed == 1

        test_session.expire_all()
        updated = await repo.get_message(test_session, message_id)
        assert updated is not None
        assert updated.embedding_status == "completed"
        assert updated.embedding is not None
