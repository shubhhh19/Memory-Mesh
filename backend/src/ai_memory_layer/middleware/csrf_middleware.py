"""CSRF protection middleware using double-submit cookie pattern."""

from __future__ import annotations

import secrets
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ai_memory_layer.config import get_settings
from ai_memory_layer.logging import get_logger

logger = get_logger(component="csrf")

# Paths that don't require CSRF protection (public endpoints, API key auth)
CSRF_EXEMPT_PATHS = {
    "/v1/admin/health",
    "/v1/admin/readiness",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/v1/auth/register",
    "/v1/auth/login",
    "/v1/auth/refresh",
    "/v1/auth/oauth/initiate",
    "/v1/auth/oauth/callback",
}

# Paths that use API key authentication (don't need CSRF as they use header-based auth)
CSRF_EXEMPT_PREFIXES = {
    "/v1/messages",  # Uses API key auth
    "/v1/memory",    # Uses API key auth
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection using double-submit cookie pattern.
    
    For browser-based authentication (JWT in cookies), this middleware:
    1. Sets a CSRF token cookie on responses
    2. Validates that the X-CSRF-Token header matches the cookie on state-changing requests
    
    API key authenticated requests are exempt as they use header-based auth.
    """

    def __init__(self, app, cookie_name: str = "csrf_token", header_name: str = "X-CSRF-Token"):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF check for exempt paths
        if self._is_exempt(request):
            return await call_next(request)
        
        # Skip CSRF check for requests with API key (header-based auth is CSRF-safe)
        if request.headers.get("X-API-Key"):
            return await call_next(request)
        
        # Only check CSRF for state-changing methods
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            csrf_cookie = request.cookies.get(self.cookie_name)
            csrf_header = request.headers.get(self.header_name)
            
            # If there's a cookie but no matching header, reject
            if csrf_cookie and csrf_header != csrf_cookie:
                logger.warning(
                    "csrf_validation_failed",
                    path=request.url.path,
                    method=request.method,
                    has_cookie=bool(csrf_cookie),
                    has_header=bool(csrf_header),
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token validation failed"},
                )
        
        response = await call_next(request)
        
        # Set CSRF token cookie if not present
        if self.cookie_name not in request.cookies:
            csrf_token = secrets.token_urlsafe(32)
            is_production = self.settings.environment.lower() in ("production", "prod", "staging")
            response.set_cookie(
                self.cookie_name,
                csrf_token,
                httponly=False,  # Must be readable by JavaScript
                secure=is_production,  # Only over HTTPS in production
                samesite="strict",  # Strict same-site policy
                max_age=86400,  # 24 hours
            )
        
        return response

    def _is_exempt(self, request: Request) -> bool:
        """Check if the request path is exempt from CSRF protection."""
        path = request.url.path
        
        # Exact path matches
        if path in CSRF_EXEMPT_PATHS:
            return True
        
        # Prefix matches (for API key authenticated endpoints)
        for prefix in CSRF_EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        
        # GET, HEAD, OPTIONS are always safe
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        return False
