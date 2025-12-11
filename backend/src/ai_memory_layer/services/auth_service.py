"""Authentication service for user management and JWT tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.config import get_settings
from ai_memory_layer.models.user import APIKey, User, UserRole, UserSession
from ai_memory_layer.schemas.auth import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    secret_key = settings.jwt_secret_key
    
    # Only enforce in production - config.py already validates this
    if settings.environment in ("production", "prod", "staging"):
        if secret_key == "change-me-in-production" or not secret_key or len(secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure random value (min 32 chars) in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    elif not secret_key:
        raise ValueError("JWT_SECRET_KEY must be set")
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    settings = get_settings()
    secret_key = settings.jwt_secret_key
    
    # Only enforce in production - config.py already validates this
    if settings.environment in ("production", "prod", "staging"):
        if secret_key == "change-me-in-production" or not secret_key or len(secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure random value (min 32 chars) in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    elif not secret_key:
        raise ValueError("JWT_SECRET_KEY must be set")
    
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    settings = get_settings()
    secret_key = settings.jwt_secret_key
    
    # Only enforce in production - config.py already validates this
    if settings.environment in ("production", "prod", "staging"):
        if secret_key == "change-me-in-production" or not secret_key or len(secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure random value (min 32 chars) in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    elif not secret_key:
        raise ValueError("JWT_SECRET_KEY must be set")
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        user_id: UUID | None = UUID(payload.get("sub")) if payload.get("sub") else None
        email: str | None = payload.get("email")
        username: str | None = payload.get("username")
        role: str | None = payload.get("role")
        tenant_id: str | None = payload.get("tenant_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            user_id=user_id,
            email=email,
            username=username,
            role=role,
            tenant_id=tenant_id,
        )
        return token_data
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def hash_api_key(key: str) -> str:
    """Hash an API key for storage using bcrypt."""
    # Use bcrypt for API key hashing to resist brute force attacks
    return pwd_context.hash(key)


def verify_api_key_hash(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its bcrypt hash."""
    return pwd_context.verify(plain_key, hashed_key)


def generate_api_key() -> str:
    """Generate a new API key."""
    return f"mm_{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Service for authentication operations."""

    async def create_user(
        self,
        session: AsyncSession,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
        tenant_id: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        stmt = select(User).where((User.email == email) | (User.username == username))
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.email == email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            tenant_id=tenant_id,
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def authenticate_user(
        self,
        session: AsyncSession,
        email: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> User | None:
        """Authenticate a user by email/username and password."""
        if not password:
            return None
        
        if email:
            stmt = select(User).where(User.email == email)
        elif username:
            stmt = select(User).where(User.username == username)
        else:
            return None
        
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # OAuth users don't have passwords
        if not user.hashed_password:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await session.commit()
        
        return user

    async def get_user_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        """Get a user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Get a user by email."""
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_api_key(
        self,
        session: AsyncSession,
        user_id: UUID,
        name: str,
        expires_days: int | None = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user."""
        key = generate_api_key()
        key_hash = hash_api_key(key)
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            expires_at=expires_at,
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return api_key, key

    async def verify_api_key(self, session: AsyncSession, api_key: str) -> User | None:
        """Verify an API key and return the associated user."""
        # Fetch all active API keys and verify with bcrypt
        # This is necessary because bcrypt hashes include random salts
        stmt = select(APIKey).where(APIKey.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        api_keys = result.scalars().all()
        
        api_key_obj = None
        for key_obj in api_keys:
            if verify_api_key_hash(api_key, key_obj.key_hash):
                api_key_obj = key_obj
                break
        
        if not api_key_obj:
            return None
        
        # Check expiration
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now(timezone.utc):
            return None
        
        # Update last used
        api_key_obj.last_used = datetime.now(timezone.utc)
        await session.commit()
        
        # Get user
        user = await self.get_user_by_id(session, api_key_obj.user_id)
        if user and not user.is_active:
            return None
        
        return user

    async def create_session(
        self,
        session: AsyncSession,
        user_id: UUID,
        token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_delta: timedelta | None = None,
    ) -> UserSession:
        """Create a new user session."""
        token_hash = hash_token(token)
        
        if expires_delta:
            expires_at = datetime.now(timezone.utc) + expires_delta
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        user_session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        session.add(user_session)
        await session.commit()
        await session.refresh(user_session)
        return user_session

    async def get_session(self, session: AsyncSession, token: str) -> UserSession | None:
        """Get a session by token."""
        token_hash = hash_token(token)
        stmt = select(UserSession).where(UserSession.token_hash == token_hash)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_session(self, session: AsyncSession, token: str) -> None:
        """Delete a user session."""
        user_session = await self.get_session(session, token)
        if user_session:
            await session.delete(user_session)
            await session.commit()

    async def cleanup_expired_sessions(self, session: AsyncSession) -> int:
        """Clean up expired sessions."""
        from sqlalchemy import delete
        
        now = datetime.now(timezone.utc)
        stmt = delete(UserSession).where(UserSession.expires_at < now)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0

    async def get_or_create_oauth_user(
        self,
        session: AsyncSession,
        provider: str,
        oauth_id: str,
        email: str,
        username: str,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        """Get or create a user from OAuth provider data."""
        # Check if user exists with this OAuth provider
        stmt = select(User).where(
            User.oauth_provider == provider,
            User.oauth_id == oauth_id
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update user info from OAuth
            user.full_name = full_name or user.full_name
            user.avatar_url = avatar_url or user.avatar_url
            user.last_login = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(user)
            return user
        
        # Check if user exists with this email (link accounts)
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Link OAuth to existing account
            existing_user.oauth_provider = provider
            existing_user.oauth_id = oauth_id
            existing_user.avatar_url = avatar_url or existing_user.avatar_url
            existing_user.last_login = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(existing_user)
            return existing_user
        
        # Create new user
        # Ensure unique username
        base_username = username
        counter = 1
        while True:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                break
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=email,
            username=username,
            hashed_password=None,  # OAuth users don't have password
            full_name=full_name,
            oauth_provider=provider,
            oauth_id=oauth_id,
            avatar_url=avatar_url,
            is_verified=True,  # OAuth emails are pre-verified
            role=UserRole.USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

