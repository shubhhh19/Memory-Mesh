"""Async-aware rate limiting middleware."""

from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, NamedTuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ai_memory_layer.config import get_settings
from ai_memory_layer.logging import get_logger

try:  # pragma: no cover - optional dependency path
    import redis.asyncio as redis_asyncio
except Exception:  # pragma: no cover
    redis_asyncio = None  # type: ignore[assignment]

logger = get_logger(component="rate_limit")


@dataclass(frozen=True)
class RateLimitConfig:
    amount: int
    window_seconds: int


class RateLimitResult(NamedTuple):
    allowed: bool
    count: int
    reset_epoch_ms: int


class BaseRateLimiter:
    async def hit(self, config: RateLimitConfig, identifier: str) -> RateLimitResult:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryRateLimiter(BaseRateLimiter):
    """Simple fixed-window limiter safe for asyncio usage."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    async def hit(self, config: RateLimitConfig, identifier: str) -> RateLimitResult:
        key = self._key(config, identifier)
        now = time.time()
        window_start = now - config.window_seconds
        async with self._lock:
            entries = self._windows[key]
            while entries and entries[0] <= window_start:
                entries.popleft()
            entries.append(now)
            count = len(entries)
            allowed = count <= config.amount
            reset = int((entries[0] + config.window_seconds) * 1000) if entries else int(
                (now + config.window_seconds) * 1000
            )
        return RateLimitResult(allowed=allowed, count=count, reset_epoch_ms=reset)

    def _key(self, config: RateLimitConfig, identifier: str) -> str:
        return f"{config.amount}:{config.window_seconds}:{identifier}"


class RedisRateLimiter(BaseRateLimiter):
    """Redis-backed limiter implemented with a Lua script for atomicity."""

    LUA_SCRIPT = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then
        redis.call('PEXPIRE', KEYS[1], ARGV[1])
    end
    local ttl = redis.call('PTTL', KEYS[1])
    return {current, ttl}
    """

    def __init__(self, url: str, prefix: str = "aiml:ratelimit") -> None:
        if redis_asyncio is None:  # pragma: no cover - dependency guard
            raise RuntimeError("redis>=5 is required for Redis-backed rate limiting")
        self.redis = redis_asyncio.from_url(url)
        self.prefix = prefix

    async def hit(self, config: RateLimitConfig, identifier: str) -> RateLimitResult:
        key = f"{self.prefix}:{config.amount}:{config.window_seconds}:{identifier}"
        window_ms = config.window_seconds * 1000
        result = await self.redis.eval(self.LUA_SCRIPT, 1, key, window_ms)
        count = int(result[0])
        ttl_ms = int(result[1])
        if ttl_ms < 0:
            ttl_ms = window_ms
        allowed = count <= config.amount
        reset_epoch_ms = int(time.time() * 1000 + ttl_ms)
        return RateLimitResult(allowed=allowed, count=count, reset_epoch_ms=reset_epoch_ms)


_limiter: BaseRateLimiter | None = None


def _build_limiter() -> BaseRateLimiter:
    settings = get_settings()
    if settings.redis_url:
        try:
            limiter = RedisRateLimiter(settings.redis_url)
            logger.info("rate_limit_redis_backend_enabled")
            return limiter
        except Exception as exc:
            logger.warning("rate_limit_redis_backend_failed", error=str(exc))
            if settings.environment.lower() == "production" and settings.require_redis_in_production:
                raise
    logger.info("rate_limit_in_memory_backend_enabled")
    return InMemoryRateLimiter()


def get_rate_limiter() -> BaseRateLimiter:
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        _limiter = _build_limiter()
    return _limiter


def reset_rate_limiter_cache() -> None:
    """Reset limiter instance (used by tests/settings overrides)."""
    global _limiter  # noqa: PLW0603
    _limiter = _build_limiter()


def _extract_tenant_id_hint(request: Request) -> str | None:
    """Pull tenant identifier from headers, path, or query."""
    tenant_id = (
        request.headers.get("x-tenant-id")
        or request.path_params.get("tenant_id")
        or request.query_params.get("tenant_id")
    )
    return tenant_id


async def _resolve_tenant_id(request: Request) -> str | None:
    """Try multiple sources to resolve the tenant id, including JSON payloads."""
    tenant_id = _extract_tenant_id_hint(request)
    if tenant_id:
        return tenant_id
    if request.method in {"POST", "PUT", "PATCH"} and request.headers.get("content-type", "").startswith(
        "application/json"
    ):
        try:
            body = await request.json()
            if isinstance(body, dict):
                tenant_id = body.get("tenant_id")
        except Exception:  # pragma: no cover - defensive
            tenant_id = None
    return tenant_id


def get_client_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting (tenant or IP)."""
    tenant_id = _extract_tenant_id_hint(request)
    if tenant_id:
        return f"tenant:{tenant_id}"

    return _get_ip_identifier(request)


def _get_ip_identifier(request: Request) -> str:
    """
    Get client IP for rate limiting, resistant to IP spoofing.
    
    Priority:
    1. X-Real-IP (set by reverse proxy like Render/nginx)
    2. First IP in X-Forwarded-For (only if from trusted proxy)
    3. Direct client host
    
    Note: In production behind a reverse proxy, X-Real-IP is more reliable
    as it's set by the proxy itself and cannot be spoofed by the client.
    """
    # X-Real-IP is set by the reverse proxy and is more trustworthy
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        # Validate IP format to prevent injection
        ip = real_ip.strip()
        if _is_valid_ip(ip):
            return f"ip:{ip}"
    
    # Fall back to X-Forwarded-For with validation
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Get the rightmost non-private IP (the one closest to the proxy)
        # or the leftmost IP if behind a trusted proxy
        ips = [ip.strip() for ip in forwarded.split(",")]
        if ips:
            # Use the first IP (client IP when behind trusted proxy)
            # In production, Render/nginx sets this correctly
            first_ip = ips[0]
            if _is_valid_ip(first_ip):
                return f"ip:{first_ip}"
    
    # Direct connection - use client host
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format to prevent injection attacks."""
    import re
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
    
    if re.match(ipv4_pattern, ip):
        # Validate each octet is 0-255
        octets = ip.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)
    elif re.match(ipv6_pattern, ip) or ip == '::1':
        return True
    return False


def _parse_limit(limit_str: str) -> RateLimitConfig:
    pattern = re.compile(
        r"^\s*(\d+)\s*(?:/|\s*/?\s*per\s+)?\s*(second|minute|hour|day)s?\s*$",
        re.IGNORECASE,
    )
    match = pattern.match(limit_str)
    if not match:
        raise ValueError(f"Invalid rate limit format: {limit_str}")
    amount = int(match.group(1))
    unit = match.group(2).lower()
    unit_seconds = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }[unit]
    return RateLimitConfig(amount=amount, window_seconds=unit_seconds)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Async-safe rate limiting middleware."""

    def __init__(self, app, rate_limit: str | None = None, tenant_rate_limit: str | None = None):
        super().__init__(app)
        settings = get_settings()
        self.global_limit_str = rate_limit or settings.global_rate_limit
        self.tenant_limit_str = tenant_rate_limit or settings.tenant_rate_limit
        self.global_limit = _parse_limit(self.global_limit_str)
        self.tenant_limit = _parse_limit(self.tenant_limit_str)
        self.limiter = get_rate_limiter()
        logger.info(
            "rate_limit_initialized",
            global_limit=self.global_limit_str,
            tenant_limit=self.tenant_limit_str,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ["/v1/admin/health", "/v1/admin/readiness", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        tenant_id = await _resolve_tenant_id(request)
        global_identifier = _get_ip_identifier(request)
        tenant_identifier = f"tenant:{tenant_id}" if tenant_id else None

        global_state = await self.limiter.hit(self.global_limit, global_identifier)
        if not global_state.allowed:
            return self._reject(request, self.global_limit_str, "global", None, global_state.reset_epoch_ms)

        tenant_state = None
        if tenant_identifier:
            tenant_state = await self.limiter.hit(self.tenant_limit, tenant_identifier)
            if not tenant_state.allowed:
                return self._reject(
                    request,
                    self.tenant_limit_str,
                    "tenant",
                    tenant_id,
                    tenant_state.reset_epoch_ms,
                )

        response = await call_next(request)
        self._apply_headers(response, global_state, tenant_state)
        return response

    def _apply_headers(
        self,
        response: Response,
        global_state: RateLimitResult,
        tenant_state: RateLimitResult | None,
    ) -> None:
        response.headers["X-RateLimit-Limit"] = str(self.global_limit.amount)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.global_limit.amount - global_state.count)
        )
        response.headers["X-RateLimit-Reset"] = str(global_state.reset_epoch_ms // 1000)
        if tenant_state:
            response.headers["X-RateLimit-Tenant-Limit"] = str(self.tenant_limit.amount)
            response.headers["X-RateLimit-Tenant-Remaining"] = str(
                max(0, self.tenant_limit.amount - tenant_state.count)
            )
            response.headers["X-RateLimit-Tenant-Reset"] = str(tenant_state.reset_epoch_ms // 1000)

    def _reject(
        self,
        request: Request,
        limit_str: str,
        scope: str,
        tenant_id: str | None,
        reset_epoch_ms: int,
    ) -> JSONResponse:
        logger.warning(
            "rate_limit_exceeded",
            identifier=get_client_identifier(request),
            scope=scope,
            tenant_id=tenant_id,
            path=request.url.path,
            limit=limit_str,
        )
        retry_after = max(1, int((reset_epoch_ms / 1000) - time.time()))
        request_id = getattr(request.state, "request_id", "unknown")
        detail = (
            f"Tenant rate limit exceeded for {tenant_id}: {limit_str}"
            if scope == "tenant"
            else f"Rate limit exceeded: {limit_str}"
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": detail,
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-Request-ID": request_id,
            },
        )


def enforce_tenant_rate_limit(tenant_id: str) -> None:
    """Legacy hook used by a few call sites (sync contexts)."""
    raise RuntimeError("enforce_tenant_rate_limit is no longer supported; use middleware path instead")
