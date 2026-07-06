"""
Fixtures compartilhadas por toda a suíte de testes.

Configura o banco de dados real (Postgres) para os testes de integração e API.
Cada teste roda dentro de uma transação isolada que sofre rollback ao final,
garantindo que o banco continue limpo sem precisar recriar as tabelas do zero.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.base import Base
from app.main import create_app
from app.models import (  # noqa: F401
    permission_model,
    refresh_token_model,
    role_model,
    session_model,
    user_model,
)


@pytest_asyncio.fixture
async def _engine():
    """
    Engine de teste criada a cada função (escopo de função).

    Nota de decisão: Inicialmente esta fixture tinha o escopo de sessão, mas isso quebrava
    o `pytest-asyncio`, que abre um loop de eventos novo para cada teste. Como a engine e
    as conexões ficam presas ao loop onde nasceram, tentar reaproveitá-las causava erros
    de loop fechado e operações concorrentes travadas. O escopo de função garante que a
    engine use sempre o mesmo loop do teste atual. Como o banco é pequeno, o custo de
    recriar as tabelas a cada teste é insignificante.
    """

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
    Sessão de banco para cada teste, rodando dentro de uma transação isolada.
    Ao final do teste, um rollback é executado. Isso garante um banco limpo
    para o próximo teste, sem o custo de recriar as tabelas do zero.
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


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limit_counters() -> AsyncGenerator[None, None]:
    """
    Zera o Redis de rate limit antes de cada teste e corrige problemas de loop de eventos.
    Mudar o loop a cada teste quebra o cliente do Redis guardado em cache (lru_cache),
    causando erros de loop fechado. Limpar o cache aqui força a criação de um cliente
    novo para o loop de eventos do teste atual.
    """

    from app.integrations.redis_client import get_redis_client

    get_redis_client.cache_clear()
    redis_client = get_redis_client()
    await redis_client.flushdb()
    yield
    await redis_client.aclose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP assíncrono para testar as rotas da aplicação FastAPI.

    A dependência do banco de dados é substituída para usar a mesma sessão
    com rollback do teste (`db_session`), garantindo o isolamento dos dados.
    """

    from app.api.dependencies.db_dependency import get_db

    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
