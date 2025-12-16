"""
Test utilities for Memory Mesh tests.

This module provides common utilities and fixtures for testing.
"""

from typing import Any, AsyncGenerator
from unittest.mock import MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from ai_memory_layer.models.base import Base


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create an in-memory SQLite database for testing.
    
    This fixture creates a fresh database for each test and cleans up afterwards.
    """
    # Create in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock embedding service for testing."""
    mock = MagicMock()
    mock.generate_embedding.return_value = [0.1] * 768  # Mock 768-dim embedding
    mock.generate_embeddings.return_value = [[0.1] * 768]
    return mock


@pytest.fixture
def sample_message_data() -> dict[str, Any]:
    """Provide sample message data for testing."""
    return {
        "tenant_id": "test-tenant",
        "conversation_id": "test-conversation",
        "role": "user",
        "content": "This is a test message",
        "importance": 0.5,
    }


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Provide sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePassword123!",
    }


def create_mock_user(
    user_id: str = "test-user-id",
    email: str = "test@example.com",
    username: str = "testuser",
) -> MagicMock:
    """Create a mock user object."""
    mock = MagicMock()
    mock.id = user_id
    mock.email = email
    mock.username = username
    mock.is_active = True
    mock.role = "user"
    return mock


def create_mock_message(
    message_id: str = "test-message-id",
    content: str = "Test message",
    tenant_id: str = "test-tenant",
    conversation_id: str = "test-conversation",
) -> MagicMock:
    """Create a mock message object."""
    mock = MagicMock()
    mock.id = message_id
    mock.content = content
    mock.tenant_id = tenant_id
    mock.conversation_id = conversation_id
    mock.role = "user"
    mock.importance_score = 0.5
    mock.embedding = [0.1] * 768
    return mock


class AsyncMock(MagicMock):
    """Mock class that supports async calls."""
    
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return super().__call__(*args, **kwargs)
