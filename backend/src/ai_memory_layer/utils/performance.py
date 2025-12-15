"""
Performance monitoring utilities for Memory Mesh.

This module provides utilities for tracking and logging performance metrics.
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator
import logging

logger = logging.getLogger(__name__)


@contextmanager
def timer(operation_name: str, log_level: int = logging.INFO) -> Generator[None, None, None]:
    """
    Context manager to time operations.
    
    Usage:
        with timer("database_query"):
            # Your code here
            pass
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        logger.log(log_level, f"{operation_name} took {elapsed:.4f} seconds")


def time_function(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to time function execution.
    
    Usage:
        @time_function
        def my_function():
            pass
    """
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            logger.info(f"{func.__name__} took {elapsed:.4f} seconds")
    
    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            logger.info(f"{func.__name__} took {elapsed:.4f} seconds")
    
    # Return appropriate wrapper based on whether function is async
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


class PerformanceTracker:
    """Track performance metrics for operations."""
    
    def __init__(self) -> None:
        self.metrics: dict[str, list[float]] = {}
    
    def record(self, operation: str, duration: float) -> None:
        """Record a performance metric."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> dict[str, float] | None:
        """Get statistics for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return None
        
        durations = self.metrics[operation]
        return {
            "count": len(durations),
            "total": sum(durations),
            "avg": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
        }
    
    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """Get statistics for all operations."""
        return {
            operation: stats
            for operation in self.metrics
            if (stats := self.get_stats(operation)) is not None
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()


# Global performance tracker instance
_tracker = PerformanceTracker()


def get_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return _tracker
