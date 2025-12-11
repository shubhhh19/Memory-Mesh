"""Standalone worker process for embedding jobs."""

from __future__ import annotations

import asyncio
import contextlib
import signal

from ai_memory_layer.config import get_settings
from ai_memory_layer.logging import configure_logging, get_logger
from ai_memory_layer.services.job_queue import EmbeddingJobQueue

configure_logging()
logger = get_logger(component="embedding_worker")


async def _serve(queue: EmbeddingJobQueue) -> None:
    """Run the worker until a termination signal is received."""
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _handle_stop)

    await queue.start()
    await stop_event.wait()
    await queue.stop()


def run() -> None:
    """Entry point for the worker CLI."""
    settings = get_settings()
    if not settings.async_embeddings:
        logger.error("async_embeddings_disabled", message="Enable MEMORY_ASYNC_EMBEDDINGS to run worker")
        return

    queue = EmbeddingJobQueue()
    try:
        asyncio.run(_serve(queue))
    except KeyboardInterrupt:  # pragma: no cover - interactive path
        logger.info("worker_shutdown_requested")


if __name__ == "__main__":
    run()
