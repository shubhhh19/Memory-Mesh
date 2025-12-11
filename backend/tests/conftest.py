"""Shared pytest fixtures for testing."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

os.environ.setdefault("AIML_USE_PGVECTOR_STUB", "1")

pytest_plugins = ("pytest_asyncio",)

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ai_memory_layer import config as settings_module
from ai_memory_layer.rate_limit import reset_rate_limiter_cache
from ai_memory_layer.database import Base, get_session
from ai_memory_layer.main import create_app
from ai_memory_layer.services.message_service import MessageService


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """In-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Test database session."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def test_app() -> FastAPI:
    return create_app()


@pytest.fixture
def client_builder(test_session: AsyncSession):
    """Factory for creating API clients after optional settings overrides."""

    @asynccontextmanager
    async def _builder():
        app = create_app()

        # Ensure services respect the current settings overrides for each test
        from ai_memory_layer.routes import memory, messages

        shared_service = MessageService()
        messages.service = shared_service
        memory.service = shared_service

        async def override_get_session():
            yield test_session

        app.dependency_overrides[get_session] = override_get_session
        # Also override get_read_session for search endpoint
        from ai_memory_layer.database import get_read_session
        app.dependency_overrides[get_read_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        app.dependency_overrides.clear()

    return _builder


@pytest.fixture
async def client(client_builder) -> AsyncIterator[AsyncClient]:
    async with client_builder() as ac:
        yield ac


@pytest.fixture
def settings_override() -> Callable[..., Any]:
    """Override settings via environment variables within a test."""

    def _override(**overrides: Any):
        reset_rate_limiter_cache()
        return settings_module.override_settings(**overrides)

    yield _override
    settings_module.reset_overrides()
    reset_rate_limiter_cache()


@pytest.fixture(autouse=True)
def _default_settings(settings_override):
    return settings_override(
        embedding_provider="mock",
        async_embeddings=False,
        retention_schedule_seconds=0,
        retention_tenants=[],
        allowed_origins="*",
        global_rate_limit="200/minute",
        request_timeout_seconds=30,
    )
