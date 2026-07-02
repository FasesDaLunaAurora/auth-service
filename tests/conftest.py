"""
Fixtures compartilhadas por toda a suíte de testes.

Segue a Seção 9: os testes de integração/API rodam contra um **banco de
dados real** (o mesmo Postgres apontado por `DATABASE_URL`, tipicamente
um container descartável — ver `.github/workflows/ci.yml`), não um mock
de banco. Cada teste roda dentro de uma transação que é revertida ao
final (`rollback`), garantindo isolamento sem precisar recriar o schema
a cada teste.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.base import Base
from app.main import create_app

# Importa todos os models para que `Base.metadata` os conheça antes do
# `create_all` — mesmo motivo do import em `alembic/env.py`.
from app.models import (  # noqa: F401
    permission_model,
    refresh_token_model,
    role_model,
    session_model,
    user_model,
)


@pytest_asyncio.fixture(scope="session")
async def _engine():
    """Engine de teste, criada uma vez por sessão de testes."""
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Sessão de banco por teste, dentro de uma transação revertida ao
    final — cada teste enxerga um banco "limpo", sem custo de recriar
    tabelas a cada execução.
    """
    connection = await _engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP assíncrono (`httpx.AsyncClient`) contra a aplicação
    FastAPI real, com a dependência de banco sobrescrita para usar a
    sessão transacional do teste (`db_session`).
    """
    from app.api.dependencies.db_dependency import get_db

    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
