"""
Ambiente de execução do Alembic, configurado para engine assíncrona.

Importa `Base.metadata` (via `app/database/base.py`) e, futuramente, todos
os `models` (Etapa 2), para que `alembic revision --autogenerate` consiga
detectar o schema completo. A URL de conexão é obtida de
`app.core.config.settings`, nunca duplicada em `alembic.ini`.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.database.base import Base

# Importar todos os módulos de `app.models` aqui garante que suas classes
# sejam registradas em `Base.metadata` antes do autogenerate.
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

# Sobrescreve a URL do `alembic.ini` com a URL validada via Pydantic
# Settings — mantém uma única fonte de verdade para a connection string.
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))


def run_migrations_offline() -> None:
    """Executa migrações em modo 'offline' (gera SQL sem conectar ao banco)."""
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
    """Executa migrações em modo 'online', usando uma engine assíncrona real."""
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
