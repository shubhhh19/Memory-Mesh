"""Health reporting service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_memory_layer import __version__
from ai_memory_layer.config import get_settings
from ai_memory_layer.database import check_database_health
from ai_memory_layer.services.embedding import build_embedding_service
from ai_memory_layer.logging import get_logger

logger = get_logger(component="health")


@dataclass
class HealthReport:
    status: str
    database: str
    latency_ms: float | None
    uptime_seconds: float
    environment: str
    version: str
    timestamp: datetime
    notes: str | None = None
    embedding: str = "unknown"
    redis: str = "unknown"


async def check_redis_health() -> tuple[bool, float | None]:
    """Check Redis connectivity and return status and latency."""
    settings = get_settings()
    if not settings.redis_url:
        return True, None  # Redis not configured, that's okay
    
    try:
        import redis.asyncio as redis_asyncio
        import time
        
        start = time.perf_counter()
        redis_client = redis_asyncio.from_url(settings.redis_url)
        await asyncio.wait_for(redis_client.ping(), timeout=3.0)
        latency = time.perf_counter() - start
        await redis_client.close()
        return True, latency
    except ImportError:
        logger.warning("redis_not_installed", message="redis package not installed")
        return True, None  # Redis package not installed, but that's okay
    except asyncio.TimeoutError:
        logger.warning("redis_health_timeout")
        return False, None
    except Exception as e:
        logger.warning("redis_health_failed", error=str(e))
        return False, None


class HealthService:
    """Produces health responses with timing metadata."""

    def __init__(self, start_time: datetime) -> None:
        self.start_time = start_time

    async def build_liveness(self) -> HealthReport:
        settings = get_settings()
        db_ok, latency = await check_database_health()
        latency_ms = latency * 1000 if latency is not None else None
        status = "ok" if db_ok else "down"
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return HealthReport(
            status=status,
            database="ok" if db_ok else "down",
            latency_ms=latency_ms,
            uptime_seconds=uptime,
            environment=settings.environment,
            version=__version__,
            timestamp=datetime.now(timezone.utc),
            embedding="skipped",
            redis="skipped",
            notes=None,
        )

    async def build_readiness(self) -> HealthReport:
        settings = get_settings()
        
        # Check database health
        db_ok, latency = await check_database_health()
        latency_ms = latency * 1000 if latency is not None else None
        
        # Check Redis health
        redis_ok, redis_latency = await check_redis_health()
        redis_status = "ok" if redis_ok else "failed"
        if not settings.redis_url:
            redis_status = "not_configured"
        
        # Check embedding service health
        embed_status = "ok"
        if settings.health_embed_check_enabled:
            try:
                embedder = build_embedding_service(settings.embedding_provider)
                await asyncio.wait_for(
                    embedder.embed("healthcheck"),
                    timeout=settings.readiness_embed_timeout_seconds,
                )
            except Exception:
                embed_status = "failed"
        else:
            embed_status = "skipped"
        
        # Determine overall status
        all_critical_ok = db_ok and (redis_ok or not settings.redis_url)
        if all_critical_ok and embed_status in ("ok", "skipped"):
            status = "ok"
        elif all_critical_ok:
            status = "degraded"
        else:
            status = "down"
        
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        # Build notes
        notes_parts = []
        if embed_status not in ("ok", "skipped"):
            notes_parts.append("embedding check failed")
        if not redis_ok and settings.redis_url:
            notes_parts.append("redis check failed")
        notes = "; ".join(notes_parts) if notes_parts else None
        
        return HealthReport(
            status=status,
            database="ok" if db_ok else "down",
            latency_ms=latency_ms,
            uptime_seconds=uptime,
            environment=settings.environment,
            version=__version__,
            timestamp=datetime.now(timezone.utc),
            embedding=embed_status,
            redis=redis_status,
            notes=notes,
        )
