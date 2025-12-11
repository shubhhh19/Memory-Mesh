"""Persistent background job processing for embeddings."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager, suppress
from typing import Callable, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.config import get_settings
from ai_memory_layer.database import session_scope
from ai_memory_layer.logging import get_logger
from ai_memory_layer.models.memory import EmbeddingJob
from ai_memory_layer.repositories.memory_repository import MemoryRepository
from ai_memory_layer.services.message_service import MessageService

logger = get_logger(component="embedding_job_queue")


class EmbeddingJobQueue:
    """Simple in-process, persistent job runner for embedding jobs."""

    def __init__(
        self,
        *,
        service: MessageService | None = None,
        repository: MemoryRepository | None = None,
        poll_interval: float | None = None,
        batch_size: int | None = None,
        session_provider: Callable[[], AbstractAsyncContextManager[AsyncSession]]
        | None = None,
    ) -> None:
        settings = get_settings()
        self.poll_interval = poll_interval or settings.embedding_job_poll_seconds
        self.batch_size = batch_size or settings.embedding_job_batch_size
        self.max_attempts = settings.embedding_job_max_attempts
        self.retry_backoff_seconds = settings.embedding_job_retry_backoff_seconds
        self.repository = repository or MemoryRepository()
        self.service = service or MessageService()
        self.session_provider = session_provider or session_scope
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background job processor."""
        if not get_settings().async_embeddings:
            logger.info("embedding_job_queue_disabled")
            return
        if self._task:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="embedding-job-queue")
        logger.info("embedding_job_queue_started")

    async def stop(self) -> None:
        """Stop the background processor."""
        if not self._task:
            return
        self._stop_event.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("embedding_job_queue_stopped")

    async def _run(self) -> None:
        """Run the job loop."""
        try:
            while not self._stop_event.is_set():
                processed = await self.drain_once()
                # If work was processed, loop immediately to drain remaining jobs.
                # Otherwise, sleep for the configured poll interval.
                sleep_for = 0.0 if processed else self.poll_interval
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_for)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:  # pragma: no cover - cancellation path
            raise
        except Exception:
            logger.exception("embedding_job_queue_crashed")
            # Attempt a graceful restart unless we are shutting down
            if not self._stop_event.is_set():
                await asyncio.sleep(self.poll_interval)
                self._task = asyncio.create_task(self._run(), name="embedding-job-queue")

    async def drain_once(self) -> int:
        """Process a batch of jobs and return how many were handled."""
        jobs = await self._claim_jobs()
        processed = 0
        for job in jobs:
            await self._process_job(job.id)
            processed += 1
        return processed

    async def _claim_jobs(self) -> Sequence[EmbeddingJob]:
        async with self.session_provider() as session:
            jobs = await self.repository.claim_embedding_jobs(
                session,
                limit=self.batch_size,
                max_attempts=self.max_attempts,
                retry_backoff_seconds=self.retry_backoff_seconds,
            )
            await session.commit()
            return jobs

    async def _process_job(self, job_id: UUID) -> None:
        async with self.session_provider() as session:
            job = await self.repository.get_embedding_job(session, job_id)
            if job is None:
                return
            message = await self.repository.get_message(session, job.message_id)
            if message is None:
                await self.repository.update_embedding_job(
                    session, job_id=job.id, status="failed", error="message_missing"
                )
                await session.commit()
                return
            try:
                await self.service._apply_embedding(
                    session,
                    message=message,
                    content=message.content,
                    explicit_importance=message.importance_score,
                )
                await session.commit()
            except Exception as exc:  # pragma: no cover - unexpected failures
                logger.exception("embedding_job_failed", job_id=str(job.id), error=str(exc))
                await self.repository.update_embedding_job(
                    session,
                    job_id=job.id,
                    status="failed",
                    error=str(exc),
                )
                await session.commit()
