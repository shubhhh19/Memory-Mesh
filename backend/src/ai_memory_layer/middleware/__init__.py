"""Middleware package."""

# Import from middleware_module.py (the original module, renamed to avoid conflict)
from ai_memory_layer.middleware_module import (
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
    request_id_ctx_var,
)

# Import versioning middleware
try:
    from ai_memory_layer.middleware.versioning_middleware import VersioningMiddleware
except ImportError:
    VersioningMiddleware = None

# Import tracing middleware (optional, requires opentelemetry)
try:
    from ai_memory_layer.middleware.tracing_middleware import TracingMiddleware
except ImportError:
    TracingMiddleware = None

# Import CSRF middleware
from ai_memory_layer.middleware.csrf_middleware import CSRFMiddleware

__all__ = [
    "RequestIDMiddleware",
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "TimeoutMiddleware",
    "VersioningMiddleware",
    "TracingMiddleware",
    "CSRFMiddleware",
    "request_id_ctx_var",
]

