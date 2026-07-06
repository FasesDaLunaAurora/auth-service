"""
Engine assíncrona e fábrica de sessões do SQLAlchemy.

Este módulo deve ser consumido apenas pelas dependências da API e testes.
Os repositórios recebem a sessão por injeção de dependência e nunca importam
este arquivo diretamente, garantindo o desacoplamento.
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
    # pool_pre_ping testa conexões ociosas antes do uso para evitar erros de queda.
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
    Gerador de sessão assíncrona para o `Depends()` do FastAPI.
    Fecha a sessão ao final da requisição e dá rollback em caso de erro,
    evitando conexões presas ou corrompidas no pool.
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
    Context manager para scripts, background jobs ou testes (fora do HTTP).
    Realiza o `commit()` automático ao final do bloco `with` se não houver erros.
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
    """Fecha todas as conexões do pool no shutdown da aplicação."""
    await engine.dispose()
