import pytest

from ai_memory_layer.schemas.messages import MessageCreate
from ai_memory_layer.services.message_service import MessageService


@pytest.mark.asyncio
async def test_ingest_completes_embedding(test_session, settings_override):
    settings_override(async_embeddings=False)
    service = MessageService()
    payload = MessageCreate(
        tenant_id="tenant-x",
        conversation_id="conv-1",
        role="user",
        content="hello async world",
    )
    response = await service.ingest(test_session, payload)
    assert response.embedding_status == "completed"
    assert response.importance_score is not None
