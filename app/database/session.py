"""
Engine assíncrona e fábrica de sessões do SQLAlchemy 2.x.

Este módulo é consumido exclusivamente por `app/api/dependencies/db_dependency.py`
(camada de API) e por `tests/conftest.py`. A camada de `repositories` recebe
a sessão via injeção de dependência — ela nunca importa este módulo
diretamente, o que preserva o isolamento exigido pela Clean Architecture.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
    # `pool_pre_ping` evita erros de "conexão fechada pelo servidor" em
    # conexões ociosas de longa duração — importante para um serviço que
    # fica no ar 24/7.
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Gerador de sessão assíncrona para uso com `Depends()` do FastAPI.

    Fecha a sessão automaticamente ao final da requisição e faz rollback
    em caso de exceção não tratada, evitando conexões "sujas" retornarem
    ao pool.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para uso fora do ciclo de requisição HTTP (ex: scripts
    de manutenção, jobs, testes de integração de `repositories`).

    Diferente de `get_db_session`, este helper também realiza `commit()`
    automático ao final do bloco `with`, caso nenhuma exceção ocorra.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Libera todas as conexões do pool. Chamado no shutdown da aplicação."""
    await engine.dispose()
