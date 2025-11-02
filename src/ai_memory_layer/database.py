"""Database utilities and base declarative class."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ai_memory_layer.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=settings.sql_echo, future=True)


engine: AsyncEngine | None = None
SessionFactory: async_sessionmaker[AsyncSession] | None = None


async def init_engine() -> None:
    """Initialise global engine/session factory."""
    global engine, SessionFactory  # noqa: PLW0603
    if engine is None:
        engine = _build_engine()
        SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session."""
    if SessionFactory is None:
        await init_engine()
    assert SessionFactory is not None  # nosec - guarded above
    async with SessionFactory() as session:
        yield session
