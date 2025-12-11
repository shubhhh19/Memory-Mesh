"""Simple circuit breaker implementation for external calls."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, TypeVar

from ai_memory_layer.logging import get_logger

logger = get_logger(component="circuit_breaker")

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when the circuit is open and calls are short-circuited."""


class CircuitBreaker:
    """Minimal circuit breaker to protect external dependencies."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_time_seconds: int = 30,
        half_open_successes: int = 2,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_time = timedelta(seconds=recovery_time_seconds)
        self.half_open_successes = half_open_successes
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.next_attempt_at = datetime.now(timezone.utc)

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        if self.state == "open":
            if datetime.now(timezone.utc) < self.next_attempt_at:
                raise CircuitOpenError("circuit_open")
            self.state = "half_open"

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    def _record_success(self) -> None:
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.half_open_successes:
                self._close()
        else:
            self.success_count = 0
            self.failure_count = 0

    def _record_failure(self) -> None:
        self.failure_count += 1
        self.success_count = 0
        if self.failure_count >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self.state = "open"
        self.next_attempt_at = datetime.now(timezone.utc) + self.recovery_time
        logger.warning("circuit_opened", retry_after_seconds=self.recovery_time.total_seconds())

    def _close(self) -> None:
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        logger.info("circuit_closed")
