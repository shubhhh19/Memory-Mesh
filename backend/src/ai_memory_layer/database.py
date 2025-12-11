"""Database utilities and base declarative class."""

from __future__ import annotations

from contextlib import asynccontextmanager
import time
from itertools import cycle
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from tenacity import (
    retry,
    retry_if_exception_type,
    wait_exponential,
    stop_after_attempt,
)

from ai_memory_layer.config import get_settings
from ai_memory_layer.logging import get_logger

logger = get_logger(component="database")


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    database_url = settings.database_url
    return _build_engine_for_url(database_url)


def _build_engine_for_url(url: str) -> AsyncEngine:
    settings = get_settings()
    engine_kwargs = {
        "echo": settings.sql_echo,
        "future": True,
        "pool_pre_ping": True,
    }
    if "postgresql" in url or "postgres" in url:
        engine_kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_recycle": settings.database_pool_recycle,
            }
        )
    return create_async_engine(url, **engine_kwargs)


engine: AsyncEngine | None = None
SessionFactory: async_sessionmaker[AsyncSession] | None = None
read_engines: list[AsyncEngine] = []
read_session_factories: list[async_sessionmaker[AsyncSession]] = []
_read_factory_cycle: cycle | None = None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(OperationalError),
    reraise=True,
)
async def _test_connection(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
        await connection.commit()


async def init_engine() -> None:
    global engine, SessionFactory, read_engines, read_session_factories, _read_factory_cycle  # noqa: PLW0603
    if engine is None:
        engine = _build_engine()
        try:
            await _test_connection(engine)
            SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
            logger.info("database_engine_initialized", url=str(engine.url))
        except Exception as exc:
            logger.error("database_connection_failed", error=str(exc))
            raise
    settings = get_settings()
    if settings.read_replica_urls and not read_engines:
        for replica_url in settings.read_replica_urls:
            replica_engine = _build_engine_for_url(replica_url)
            await _test_connection(replica_engine)
            read_engines.append(replica_engine)
            read_session_factories.append(async_sessionmaker(replica_engine, expire_on_commit=False))
        if read_session_factories:
            _read_factory_cycle = cycle(read_session_factories)
            logger.info("read_replicas_initialized", replicas=len(read_session_factories))


@asynccontextmanager
async def _session_context(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    session = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    if SessionFactory is None:
        await init_engine()
    assert SessionFactory is not None  # nosec - guarded above
    async with _session_context(SessionFactory) as session:
        yield session


async def get_read_session() -> AsyncIterator[AsyncSession]:
    if SessionFactory is None:
        await init_engine()
    factory = _next_read_factory()
    try:
        async with _session_context(factory) as session:
            yield session
    except Exception as exc:
        if factory is not SessionFactory and read_session_factories:
            logger.warning(
                "read_session_failed_fallback",
                error=str(exc),
            )
            assert SessionFactory is not None  # nosec - guarded
            async with _session_context(SessionFactory) as session:
                yield session
        else:
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    if SessionFactory is None:
        await init_engine()
    assert SessionFactory is not None  # nosec - guarded above
    async with _session_context(SessionFactory) as session:
        yield session


async def check_database_health() -> tuple[bool, float | None]:
    if engine is None:
        await init_engine()
    assert engine is not None  # nosec - guarded
    start = time.perf_counter()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("database_health_check_failed")
        return False, None
    return True, time.perf_counter() - start


def _next_read_factory() -> async_sessionmaker[AsyncSession]:
    if read_session_factories and _read_factory_cycle is not None:
        return next(_read_factory_cycle)
    assert SessionFactory is not None  # nosec - guarded
    return SessionFactory
