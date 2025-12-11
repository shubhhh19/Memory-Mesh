"""Tracing middleware for request/response tracing."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ai_memory_layer.tracing import add_span_attributes, get_current_span, trace_request


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add tracing to requests."""

    async def dispatch(self, request: Request, call_next: callable) -> Response:
        """Process request with tracing."""
        trace_request(request)
        
        # Add request ID if available
        if hasattr(request.state, "request_id"):
            add_span_attributes({"request.id": request.state.request_id})
        
        response = await call_next(request)
        
        # Add response attributes
        span = get_current_span()
        if span:
            span.set_attribute("http.status_code", response.status_code)
        
        return response

