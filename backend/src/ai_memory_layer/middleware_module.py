"""Custom middleware utilities."""

from __future__ import annotations

import asyncio
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to each request/response pair."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx_var.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)
        response.headers["x-request-id"] = request_id
        request.state.request_id = request_id
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Abort requests that exceed the configured timeout."""

    def __init__(self, app, timeout: float) -> None:
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return Response(
                content='{"detail":"Request timeout"}',
                status_code=504,
                media_type="application/json",
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests that exceed the configured payload size.
    
    Note: This middleware only checks requests with a Content-Length header.
    For requests without Content-Length, size limiting should be handled
    by the web server (nginx, etc.) before requests reach the application.
    This avoids memory overhead from reading large request bodies.
    """

    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self.max_bytes:
                return Response(
                    content='{"detail":"Request too large"}',
                    status_code=413,
                    media_type="application/json",
                )
        # For requests without content-length header, we skip the check here
        # to avoid reading the entire body into memory. In production, configure
        # your web server (nginx, Apache, etc.) to enforce size limits at the
        # edge, which is more efficient and prevents large payloads from reaching
        # the application layer.
        
        return await call_next(request)
