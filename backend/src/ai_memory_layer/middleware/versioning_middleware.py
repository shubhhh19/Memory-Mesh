"""API versioning middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from ai_memory_layer.versioning import (
    add_deprecation_header,
    get_api_version,
    is_version_deprecated,
    is_version_supported,
)


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning."""

    async def dispatch(self, request: Request, call_next: callable) -> Response:
        """Process request with version checking."""
        # Skip version check for non-API routes
        if not request.url.path.startswith(("/v1/", "/v2/")):
            return await call_next(request)
        
        version = get_api_version(request)
        
        # Check if version is supported
        if not is_version_supported(version):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Unsupported API version",
                    "version": version.value,
                    "supported_versions": ["v1"],
                },
            )
        
        # Add version to request state
        request.state.api_version = version
        
        response = await call_next(request)
        
        # Add deprecation headers if version is deprecated
        if is_version_deprecated(version):
            add_deprecation_header(response, version)
        
        # Always add version header
        response.headers["X-API-Version"] = version.value
        
        return response

