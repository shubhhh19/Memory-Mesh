"""Prometheus metrics instrumentation."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:  # pragma: no cover - optional dependency
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False

router = APIRouter()

if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "aiml_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "aiml_request_latency_seconds",
        "Request latency in seconds",
        ["method", "path"],
    )
    MESSAGE_INGEST_COUNT = Counter(
        "aiml_messages_ingested_total",
        "Messages ingested by tenant/role/mode",
        ["tenant", "role", "mode", "status"],
    )
    MEMORY_SEARCH_COUNT = Counter(
        "aiml_memory_search_total",
        "Search requests by tenant and cache status",
        ["tenant", "cached"],
    )
    MEMORY_SEARCH_LATENCY = Histogram(
        "aiml_memory_search_latency_seconds",
        "Latency of memory search requests",
        ["cached"],
    )
    MEMORY_SEARCH_RESULTS = Histogram(
        "aiml_memory_search_results",
        "Distribution of result counts per search",
        ["tenant"],
    )
    EMBEDDING_JOB_COUNT = Counter(
        "aiml_embedding_jobs_total",
        "Embedding jobs processed by status",
        ["status"],
    )
    EMBEDDING_JOB_DURATION = Histogram(
        "aiml_embedding_job_duration_seconds",
        "Duration of embedding generation jobs",
        ["status"],
    )

    @router.get("/metrics")
    async def metrics() -> Response:
        """Expose Prometheus metrics."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    class MetricsMiddleware(BaseHTTPMiddleware):
        """Middleware that records request metrics."""

        async def dispatch(self, request: Request, call_next):
            if request.url.path == "/metrics":
                return await call_next(request)
            start = time.perf_counter()
            response = await call_next(request)
            duration = time.perf_counter() - start
            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status=str(response.status_code),
            ).inc()
            REQUEST_LATENCY.labels(method=request.method, path=request.url.path).observe(
                duration
            )
            return response

else:

    @router.get("/metrics")
    async def metrics() -> Response:  # type: ignore[override]
        return Response("metrics unavailable", media_type="text/plain")

    class MetricsMiddleware(BaseHTTPMiddleware):  # type: ignore[override]
        async def dispatch(self, request: Request, call_next):
            return await call_next(request)


def record_message_ingested(tenant_id: str, role: str, async_mode: bool, status: str) -> None:
    """Increment counters for message ingestion."""
    if not PROMETHEUS_AVAILABLE:  # pragma: no cover - optional dependency
        return
    mode = "async" if async_mode else "inline"
    MESSAGE_INGEST_COUNT.labels(
        tenant=tenant_id,
        role=role,
        mode=mode,
        status=status,
    ).inc()


def record_memory_search(
    tenant_id: str,
    result_count: int,
    cached: bool,
    duration: float,
) -> None:
    """Record memory search metrics."""
    if not PROMETHEUS_AVAILABLE:  # pragma: no cover - optional dependency
        return
    MEMORY_SEARCH_COUNT.labels(tenant=tenant_id, cached=str(cached)).inc()
    MEMORY_SEARCH_LATENCY.labels(cached=str(cached)).observe(duration)
    MEMORY_SEARCH_RESULTS.labels(tenant=tenant_id).observe(result_count)


def record_embedding_job(status: str, duration: float | None = None) -> None:
    """Record embedding job processing metrics."""
    if not PROMETHEUS_AVAILABLE:  # pragma: no cover - optional dependency
        return
    EMBEDDING_JOB_COUNT.labels(status=status).inc()
    if duration is not None:
        EMBEDDING_JOB_DURATION.labels(status=status).observe(duration)
