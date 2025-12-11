"""Authentication routes."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_session
from ai_memory_layer.models.user import User, UserRole
from ai_memory_layer.schemas.auth import (
    APIKeyCreate,
    APIKeyListResponse,
    APIKeyResponse,
    LoginRequest,
    OAuthCallbackRequest,
    OAuthLoginRequest,
    PasswordChange,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from ai_memory_layer.security import get_current_active_user, get_current_user
from ai_memory_layer.services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES, AuthService, create_access_token, create_refresh_token
from ai_memory_layer.logging import get_logger

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()
bearer_scheme = HTTPBearer()
logger = get_logger(component=__name__)

OAUTH_STATE_TTL_SECONDS = 300  # 5 minutes
OAUTH_STATE_PREFIX = "oauth:state:"
OAUTH_STATE_MAX_FALLBACK_SIZE = 1000  # Maximum entries in fallback store

# In-memory fallback for development (Redis is used in production)
_oauth_states_fallback: dict[str, tuple[str, float]] = {}

# Singleton Redis client for OAuth state operations (connection pooling)
_oauth_redis_client = None


def _cleanup_expired_states_fallback() -> None:
    """Remove expired OAuth state tokens and enforce size limit on fallback store."""
    import time
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = [k for k, (_, exp) in _oauth_states_fallback.items() if exp < current_time]
    for key in expired_keys:
        _oauth_states_fallback.pop(key, None)
    
    # Enforce size limit by removing oldest entries
    if len(_oauth_states_fallback) >= OAUTH_STATE_MAX_FALLBACK_SIZE:
        # Sort by expiration time and remove oldest entries
        sorted_items = sorted(_oauth_states_fallback.items(), key=lambda x: x[1][1])
        entries_to_remove = len(_oauth_states_fallback) - OAUTH_STATE_MAX_FALLBACK_SIZE + 100  # Remove 100 extra
        for key, _ in sorted_items[:entries_to_remove]:
            _oauth_states_fallback.pop(key, None)


async def _get_oauth_redis_client():
    """Get or create a singleton Redis client for OAuth state storage with connection pooling."""
    global _oauth_redis_client
    
    from ai_memory_layer.config import get_settings
    settings = get_settings()
    if not settings.redis_url:
        return None
    
    # Return existing client if available
    if _oauth_redis_client is not None:
        try:
            # Verify connection is still alive
            await _oauth_redis_client.ping()
            return _oauth_redis_client
        except Exception:
            # Connection is dead, reset and create new one
            _oauth_redis_client = None
    
    try:
        import redis.asyncio as redis_asyncio
        # Create client with connection pool (default pool size is 10)
        _oauth_redis_client = redis_asyncio.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        return _oauth_redis_client
    except ImportError:
        return None
    except Exception as e:
        logger.warning("oauth_redis_connection_failed", error=str(e))
        return None


async def _generate_oauth_state(redirect_uri: str) -> str:
    """Generate and store a secure OAuth state token (uses Redis in production)."""
    import time
    import json
    
    state = secrets.token_urlsafe(32)
    state_data = json.dumps({"redirect_uri": redirect_uri})
    
    # Try Redis first (production)
    redis_client = await _get_oauth_redis_client()
    if redis_client:
        try:
            await redis_client.setex(
                f"{OAUTH_STATE_PREFIX}{state}",
                OAUTH_STATE_TTL_SECONDS,
                state_data,
            )
            return state
        except Exception as e:
            logger.warning("oauth_state_redis_store_failed", error=str(e))
    
    # Fallback to in-memory (development only)
    _cleanup_expired_states_fallback()
    _oauth_states_fallback[state] = (redirect_uri, time.time() + OAUTH_STATE_TTL_SECONDS)
    return state


async def _validate_oauth_state(state: str | None) -> str | None:
    """Validate OAuth state token and return the associated redirect_uri."""
    import time
    import json
    
    if not state:
        return None
    
    # Try Redis first (production)
    redis_client = await _get_oauth_redis_client()
    if redis_client:
        try:
            state_data = await redis_client.get(f"{OAUTH_STATE_PREFIX}{state}")
            if state_data:
                # Delete to ensure one-time use
                await redis_client.delete(f"{OAUTH_STATE_PREFIX}{state}")
                data = json.loads(state_data)
                return data.get("redirect_uri")
        except Exception as e:
            logger.warning("oauth_state_redis_validate_failed", error=str(e))
    
    # Fallback to in-memory (development only)
    state_data = _oauth_states_fallback.pop(state, None)
    if not state_data:
        return None
    redirect_uri, expires_at = state_data
    if time.time() > expires_at:
        return None
    return redirect_uri


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """Register a new user. Rate limited by global middleware (5/minute recommended)."""
    """Register a new user."""
    user = await auth_service.create_user(
        session=session,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        tenant_id=user_data.tenant_id,
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Token:
    """Authenticate user and return JWT tokens. Rate limited by global middleware (10/minute recommended)."""
    """Authenticate user and return JWT tokens."""
    user = await auth_service.authenticate_user(
        session=session,
        email=login_data.email,
        username=login_data.username,
        password=login_data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    expires_delta = timedelta(days=30) if login_data.remember_me else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role.value,
        "tenant_id": user.tenant_id or "",
    }
    
    access_token = create_access_token(data=token_data, expires_delta=expires_delta)
    refresh_token = create_refresh_token(data=token_data)
    
    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await auth_service.create_session(
        session=session,
        user_id=user.id,
        token=refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_delta=timedelta(days=7),
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Token:
    """Refresh access token using refresh token."""
    from ai_memory_layer.services.auth_service import verify_token
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    if not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Verify session exists
    user_session = await auth_service.get_session(session, token)
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired",
        )
    
    # Get user
    user = await auth_service.get_user_by_id(session, token_data.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Create new tokens
    new_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role.value,
        "tenant_id": user.tenant_id or "",
    }
    
    access_token = create_access_token(data=new_token_data)
    new_refresh_token = create_refresh_token(data=new_token_data)
    
    # Update session
    await auth_service.delete_session(session, token)
    await auth_service.create_session(
        session=session,
        user_id=user.id,
        token=new_refresh_token,
        ip_address=user_session.ip_address,
        user_agent=user_session.user_agent,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Logout user by invalidating refresh token."""
    token = credentials.credentials
    await auth_service.delete_session(session, token)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """Update current user information."""
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Don't allow role changes via self-update
    if "role" in update_data:
        del update_data["role"]
    
    for key, value in update_data.items():
        if value is not None:
            setattr(current_user, key, value)
    
    await session.commit()
    await session.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Change user password."""
    from ai_memory_layer.services.auth_service import verify_password, get_password_hash
    
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await session.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> APIKeyResponse:
    """Create a new API key for the current user."""
    api_key_obj, key = await auth_service.create_api_key(
        session=session,
        user_id=current_user.id,
        name=api_key_data.name,
        expires_days=api_key_data.expires_days,
    )
    
    return APIKeyResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        key=key,
        last_used=api_key_obj.last_used,
        expires_at=api_key_obj.expires_at,
        is_active=api_key_obj.is_active,
        created_at=api_key_obj.created_at,
    )


@router.get("/api-keys", response_model=list[APIKeyListResponse])
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[APIKeyListResponse]:
    """List all API keys for the current user."""
    from sqlalchemy import select
    from ai_memory_layer.models.user import APIKey
    
    stmt = select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
    result = await session.execute(stmt)
    api_keys = result.scalars().all()
    
    return [APIKeyListResponse.model_validate(key) for key in api_keys]


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Delete an API key."""
    from sqlalchemy import select
    from uuid import UUID
    from ai_memory_layer.models.user import APIKey
    
    try:
        key_uuid = UUID(api_key_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API key ID")
    
    stmt = select(APIKey).where(APIKey.id == key_uuid, APIKey.user_id == current_user.id)
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    await session.delete(api_key)
    await session.commit()
    
    return {"message": "API key deleted successfully"}


@router.post("/oauth/initiate")
async def oauth_initiate(
    oauth_data: OAuthLoginRequest,
) -> dict[str, str]:
    """Initiate OAuth flow by generating state and returning the authorization URL."""
    from ai_memory_layer.config import get_settings
    
    settings = get_settings()
    state = await _generate_oauth_state(oauth_data.redirect_uri)
    
    if oauth_data.provider.value == "google":
        client_id = settings.google_client_id
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={oauth_data.redirect_uri}"
            f"&response_type=code"
            f"&scope=email%20profile"
            f"&state={state}"
        )
    elif oauth_data.provider.value == "github":
        client_id = settings.github_client_id
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth not configured"
            )
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={oauth_data.redirect_uri}"
            f"&scope=user:email"
            f"&state={state}"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {oauth_data.provider}"
        )
    
    return {"authorization_url": auth_url, "state": state}


@router.post("/oauth/callback", response_model=Token)
async def oauth_callback(
    callback_data: OAuthCallbackRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Token:
    """Handle OAuth callback and create/login user."""
    import httpx
    from ai_memory_layer.config import get_settings
    
    settings = get_settings()
    
    # Validate state parameter to prevent CSRF attacks
    redirect_uri = await _validate_oauth_state(callback_data.state)
    if redirect_uri is None:
        logger.warning("oauth_csrf_attempt", provider=callback_data.provider.value)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter. Please restart the OAuth flow."
        )
    
    # Exchange code for access token based on provider
    if callback_data.provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        client_id = settings.google_client_id
        client_secret = settings.google_client_secret
        
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                token_url,
                data={
                    "code": callback_data.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            
            if token_response.status_code != 200:
                error_detail = "Failed to exchange authorization code"
                try:
                    error_data = token_response.json()
                    error_detail = error_data.get("error_description", error_data.get("error", error_detail))
                    logger.error("oauth_token_exchange_failed", 
                               provider="google",
                               status=token_response.status_code,
                               error=error_detail,
                               redirect_uri=redirect_uri,
                               response=error_data)
                except Exception:
                    error_text = token_response.text[:200] if token_response.text else "No error details"
                    logger.error("oauth_token_exchange_failed", 
                               provider="google",
                               status=token_response.status_code,
                               error=error_text,
                               redirect_uri=redirect_uri)
                    error_detail = f"Failed to exchange authorization code: {error_text}"
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            # Get user info
            user_response = await client.get(
                user_info_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information"
                )
            
            user_info = user_response.json()
            
    elif callback_data.provider == "github":
        token_url = "https://github.com/login/oauth/access_token"
        user_info_url = "https://api.github.com/user"
        
        client_id = settings.github_client_id
        client_secret = settings.github_client_secret
        
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth not configured"
            )
        
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                token_url,
                data={
                    "code": callback_data.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"}
            )
            
            if token_response.status_code != 200:
                error_detail = "Failed to exchange authorization code"
                try:
                    error_data = token_response.json()
                    error_detail = error_data.get("error_description", error_data.get("error", error_detail))
                    logger.error("oauth_token_exchange_failed", 
                               provider="github",
                               status=token_response.status_code,
                               error=error_detail,
                               redirect_uri=redirect_uri,
                               response=error_data)
                except Exception:
                    error_text = token_response.text[:200] if token_response.text else "No error details"
                    logger.error("oauth_token_exchange_failed", 
                               provider="github",
                               status=token_response.status_code,
                               error=error_text,
                               redirect_uri=redirect_uri)
                    error_detail = f"Failed to exchange authorization code: {error_text}"
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            # Get user info
            user_response = await client.get(
                user_info_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information"
                )
            
            user_info = user_response.json()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {callback_data.provider}"
        )
    
    # Extract user information based on provider
    if callback_data.provider == "google":
        oauth_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name", "")
        avatar_url = user_info.get("picture")
        username = email.split("@")[0] if email else f"user_{oauth_id}"
    else:  # github
        oauth_id = str(user_info.get("id"))
        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("login", "")
        avatar_url = user_info.get("avatar_url")
        username = user_info.get("login", f"user_{oauth_id}")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by OAuth provider"
        )
    
    # Get or create user
    user = await auth_service.get_or_create_oauth_user(
        session=session,
        provider=callback_data.provider,
        oauth_id=oauth_id,
        email=email,
        username=username,
        full_name=name,
        avatar_url=avatar_url,
    )
    
    # Create tokens
    token_data_dict = {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role.value,
        "tenant_id": user.tenant_id or "",
    }
    
    access_token_str = create_access_token(data=token_data_dict)
    refresh_token_str = create_refresh_token(data=token_data_dict)
    
    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await auth_service.create_session(
        session=session,
        user_id=user.id,
        token=refresh_token_str,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_delta=timedelta(days=7),
    )
    
    return Token(
        access_token=access_token_str,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token_str,
    )
