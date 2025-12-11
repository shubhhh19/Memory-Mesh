from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from ai_memory_layer.config import get_settings
from ai_memory_layer.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configure_alembic_url() -> None:
    settings = get_settings()
    config.set_main_option("sqlalchemy.url", settings.sync_database_url())


def run_migrations_offline() -> None:
    _configure_alembic_url()
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _configure_alembic_url()
    url = config.get_main_option("sqlalchemy.url")
    print(f"Alembic using URL: {url}")
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online_async() -> None:
    """Optional async migrations for async drivers."""

    async def do_run_migrations() -> None:
        _configure_alembic_url()
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda conn: context.configure(connection=conn, target_metadata=target_metadata)
            )
            await connection.run_sync(lambda _: context.begin_transaction())
            await connection.run_sync(lambda _: context.run_migrations())

    asyncio.run(do_run_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
