import pytest

from ai_memory_layer.services.embedding import MockEmbeddingService, build_embedding_service


@pytest.mark.asyncio
async def test_mock_embedding_is_deterministic():
    service = MockEmbeddingService(dimensions=8)
    vec1 = await service.embed("hello world")
    vec2 = await service.embed("hello world")
    assert vec1 == vec2


def test_build_embedding_service_defaults_to_mock(settings_override):
    settings_override(embedding_provider="mock")
    service = build_embedding_service()
    assert isinstance(service, MockEmbeddingService)
