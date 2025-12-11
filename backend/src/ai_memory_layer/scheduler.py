"""Simple retention scheduler that runs inside the API process."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Sequence

from ai_memory_layer.config import get_settings
from ai_memory_layer.database import session_scope
from ai_memory_layer.logging import get_logger
from ai_memory_layer.repositories.memory_repository import MemoryRepository
from ai_memory_layer.services.retention import RetentionService

logger = get_logger(component="retention_scheduler")


class RetentionScheduler:
    """Periodically runs retention policies for configured tenants."""

    def __init__(
        self,
        *,
        service: RetentionService | None = None,
        interval_seconds: int | None = None,
        tenant_ids: Sequence[str] | None = None,
    ) -> None:
        settings = get_settings()
        self.interval = interval_seconds if interval_seconds is not None else settings.retention_schedule_seconds
        self.tenants = list(tenant_ids if tenant_ids is not None else settings.retention_tenants)
        self.service = service or RetentionService()
        self.repository = MemoryRepository()
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self.interval <= 0 or not self.tenants:
            return
        if self._task is None:
            self._stopped.clear()
            self._task = asyncio.create_task(self._run(), name="retention-scheduler")
            logger.info("retention_scheduler_started", tenants=self.tenants, interval=self.interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
            self._stopped.set()
            logger.info("retention_scheduler_stopped")

    async def _run(self) -> None:
        try:
            while True:
                await self.run_once()
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:  # pragma: no cover - cancellation path
            raise

    async def run_once(self) -> None:
        """Execute one full retention pass."""
        if not self.tenants:
            return
        tenant_list = self.tenants
        if self.tenants == ["*"]:
            async with session_scope() as session:
                tenant_list = list(await self.repository.list_tenants(session))
        for tenant in tenant_list:
            async with session_scope() as session:
                await self.service.run(session, tenant_id=tenant)
        logger.debug("retention_scheduler_cycle_completed", tenants=tenant_list)
