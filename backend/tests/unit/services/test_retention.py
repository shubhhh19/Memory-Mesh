import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.repositories.memory_repository import MemoryRepository
from ai_memory_layer.services.retention import RetentionService


@pytest.mark.asyncio
async def test_retention_service_respects_actions(test_session: AsyncSession):
    repo = MemoryRepository()
    service = RetentionService(repository=repo)
    result = await service.run(
        test_session,
        tenant_id="tenant",
        actions={"delete"},  # skip archive
        dry_run=True,
    )
    assert result.archived == 0
    assert result.deleted == 0
