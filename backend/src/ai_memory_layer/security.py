"""Security helpers (API key and JWT authentication)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.config import get_settings
from ai_memory_layer.database import get_session
from ai_memory_layer.models.user import User
from ai_memory_layer.schemas.auth import TokenData
from ai_memory_layer.services.auth_service import AuthService, verify_token

API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=False)
BEARER_TOKEN = HTTPBearer(auto_error=False)

auth_service = AuthService()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials | None = Security(BEARER_TOKEN),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Get current user from JWT token."""
    if not credentials:
        return None
    
    try:
        token_data = verify_token(credentials.credentials)
        if token_data.user_id:
            user = await auth_service.get_user_by_id(session, token_data.user_id)
            if user and user.is_active:
                return user
    except HTTPException:
        pass
    
    return None


async def get_current_user_from_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Get current user from API key."""
    if not api_key:
        return None
    
    # First check legacy API keys from config
    settings = get_settings()
    if settings.api_keys and api_key in settings.api_keys:
        # Legacy API key - return None (no user association)
        return None
    
    # Check database API keys
    user = await auth_service.verify_api_key(session, api_key)
    return user


async def get_current_user(
    token_user: User | None = Depends(get_current_user_from_token),
    api_key_user: User | None = Depends(get_current_user_from_api_key),
) -> User:
    """Get current authenticated user from token or API key."""
    user = token_user or api_key_user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require admin role."""
    from ai_memory_layer.models.user import UserRole
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str | None:
    """Validate incoming API key if keys are configured (legacy support)."""
    settings = get_settings()
    if not settings.api_keys:
        return None
    if api_key and api_key in settings.api_keys:
        return api_key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def get_tenant_id_from_user(user: User | None) -> str | None:
    """Extract tenant_id from user if available."""
    if user and user.tenant_id:
        return user.tenant_id
    return None
