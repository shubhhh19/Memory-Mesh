"""API versioning utilities."""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import APIRouter, Request
from fastapi.routing import APIRoute
from starlette.responses import Response


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"  # Future version


class VersionedAPIRoute(APIRoute):
    """Route that supports versioning."""

    def __init__(self, *args: Any, version: APIVersion = APIVersion.V1, **kwargs: Any):
        self.version = version
        super().__init__(*args, **kwargs)


def get_api_version(request: Request) -> APIVersion:
    """Extract API version from request."""
    # Check URL path
    path = request.url.path
    if path.startswith("/v2/"):
        return APIVersion.V2
    elif path.startswith("/v1/"):
        return APIVersion.V1
    
    # Check header
    version_header = request.headers.get("X-API-Version", "v1")
    if version_header.startswith("v"):
        try:
            return APIVersion(version_header.lower())
        except ValueError:
            pass
    
    # Default to v1
    return APIVersion.V1


def create_versioned_router(version: APIVersion) -> APIRouter:
    """Create a versioned API router."""
    return APIRouter(
        prefix=f"/{version.value}",
        tags=[f"API {version.value.upper()}"],
    )


def add_deprecation_header(response: Response, version: APIVersion, sunset_date: str | None = None):
    """Add deprecation headers to response."""
    response.headers["Deprecation"] = "true"
    response.headers["X-API-Version"] = version.value
    if sunset_date:
        response.headers["Sunset"] = sunset_date


# Version compatibility mapping
VERSION_COMPATIBILITY = {
    APIVersion.V1: {
        "supported": True,
        "deprecated": False,
        "sunset_date": None,
    },
    APIVersion.V2: {
        "supported": False,  # Not yet implemented
        "deprecated": False,
        "sunset_date": None,
    },
}


def is_version_supported(version: APIVersion) -> bool:
    """Check if an API version is supported."""
    return VERSION_COMPATIBILITY.get(version, {}).get("supported", False)


def is_version_deprecated(version: APIVersion) -> bool:
    """Check if an API version is deprecated."""
    return VERSION_COMPATIBILITY.get(version, {}).get("deprecated", False)

