"""
Configuração de ambiente do Alembic.

Decisão de implementação: como o projeto usa SQLAlchemy assíncrono
(`asyncpg`), o `env.py` padrão gerado por `alembic init` (síncrono) não
funciona diretamente. Adaptamos para rodar as migrações dentro de um
loop de eventos assíncrono via `asyncio.run`, conforme recomendado pela
própria documentação do SQLAlchemy 2.x para Alembic + engines async.

Este arquivo importa `Base.metadata` (app/database/base.py) e todos os
módulos de `app/models/*` (a serem criados na Etapa 2) para que o
autogenerate do Alembic detecte corretamente todas as tabelas.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.database.base import Base

# Importação dos modelos é necessária aqui para popular `Base.metadata`
# antes do autogenerate. Os módulos concretos serão adicionados na Etapa 2;
# o import é feito via pacote para já deixar o ponto de extensão pronto.
# from app.models import user_model, role_model, permission_model  # noqa: F401
# from app.models import refresh_token_model, session_model  # noqa: F401

config = context.config

# Sobrescreve a URL de conexão do alembic.ini com a vinda de `Settings`,
# garantindo uma única fonte de verdade para a string de conexão
# (evita divergência entre `.env` e `alembic.ini`).
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrações em modo 'offline' (apenas gera SQL, sem conectar)."""
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


def do_run_migrations(connection: Connection) -> None:
    """Configura o contexto do Alembic usando uma conexão síncrona já aberta."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Executa migrações em modo 'online', conectando de fato ao PostgreSQL.

    Cria um `AsyncEngine` a partir da configuração e delega a execução
    síncrona das migrações via `connection.run_sync`, padrão recomendado
    para uso de Alembic com engines assíncronos.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
