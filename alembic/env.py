"""
Configura o ambiente do Alembic com suporte a operações assíncronas.

Usa o `Base.metadata` e os modelos importados para que o comando
`alembic revision --autogenerate` consiga mapear o banco sozinho.
A string de conexão vem direto do `settings`, evitando duplicar no `.ini`.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context
from app.core.config import settings
from app.database.base import Base

# Importe os modelos aqui para registrá-los no metadata antes do autogenerate.
from app.models import (  # noqa: E402,F401
    permission_model,
    refresh_token_model,
    role_model,
    session_model,
    user_model,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Injeta a URL do Pydantic no Alembic para manter a string de conexão centralizada.
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))


def run_migrations_offline() -> None:
    """Roda as migrações offline gerando apenas o script SQL."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Roda as migrações online usando uma conexão assíncrona real."""
    connectable: AsyncEngine = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
