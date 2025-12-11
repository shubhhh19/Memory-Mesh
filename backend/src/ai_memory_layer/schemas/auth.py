"""Authentication and user schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OAuthProvider(str, Enum):
    """OAuth provider enumeration."""
    
    GOOGLE = "google"
    GITHUB = "github"


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be at least 8 characters with mix of letters, numbers, and special characters"
    )
    full_name: str | None = Field(None, max_length=255)
    tenant_id: str | None = Field(None, max_length=64)
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        if not (has_letter and has_number):
            raise ValueError("Password must contain both letters and numbers")
        return v


class UserUpdate(BaseModel):
    """Schema for user-initiated updates (excludes sensitive fields like role)."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    full_name: str | None = Field(None, max_length=255)
    tenant_id: str | None = Field(None, max_length=64)
    metadata: dict[str, Any] | None = None


class AdminUserUpdate(BaseModel):
    """Schema for admin-initiated user updates (includes sensitive fields)."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    full_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    role: str | None = None
    tenant_id: str | None = Field(None, max_length=64)
    metadata: dict[str, Any] | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    tenant_id: str | None
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    """Schema for authentication token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


class TokenData(BaseModel):
    """Schema for token payload data."""

    user_id: UUID | None = None
    email: str | None = None
    username: str | None = None
    role: str | None = None
    tenant_id: str | None = None


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr | None = None
    username: str | None = None
    password: str
    remember_me: bool = False


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        if not (has_letter and has_number):
            raise ValueError("Password must contain both letters and numbers")
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        if not (has_letter and has_number):
            raise ValueError("Password must contain both letters and numbers")
        return v


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255)
    expires_days: int | None = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """Schema for API key response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    key: str  # Only shown once on creation
    last_used: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class APIKeyListResponse(BaseModel):
    """Schema for listing API keys (without the actual key)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    last_used: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class OAuthLoginRequest(BaseModel):
    """Schema for OAuth login initiation."""
    
    provider: OAuthProvider
    redirect_uri: str = Field(..., description="Frontend redirect URI after OAuth completion")


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback handling."""
    
    provider: OAuthProvider
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for CSRF protection (required)")

