import pytest

from ai_memory_layer.scheduler import RetentionScheduler
from ai_memory_layer.services.retention import RetentionService


class DummyRetentionService(RetentionService):
    def __init__(self):
        super().__init__()
        self.invocations: list[str] = []

    async def run(self, session, *, tenant_id: str, actions=None, dry_run: bool = False):
        self.invocations.append(tenant_id)
        return self.invocations  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_retention_scheduler_run_once(settings_override):
    settings_override(retention_tenants=["tenant-a", "tenant-b"])
    scheduler = RetentionScheduler(
        service=DummyRetentionService(),
        interval_seconds=0,
        tenant_ids=["tenant-a", "tenant-b"],
    )
    await scheduler.run_once()
    assert set(scheduler.tenants) == {"tenant-a", "tenant-b"}
