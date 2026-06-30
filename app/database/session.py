"""
Gerenciamento do engine assíncrono e das sessões do SQLAlchemy.

Este módulo é a única fonte de verdade sobre como obter uma `AsyncSession`.
A camada `api/dependencies/db_dependency.py` (Etapa 8) apenas reexporta
`get_db_session` definido aqui — `repositories` nunca criam sessões
próprias, apenas recebem uma sessão já aberta (Repository Pattern, Seção 1).
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
from app.core.logging import get_logger

logger = get_logger(__name__)


def _create_engine() -> AsyncEngine:
    """
    Cria o engine assíncrono do SQLAlchemy.

    `pool_pre_ping=True` é uma decisão de implementação não explicitada na
    especificação: evita erros de conexão "stale" em deployments de longa
    duração (ex: após failover do PostgreSQL), alinhado ao princípio de
    programação defensiva da Seção 1.
    """
    return create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        future=True,
    )


engine: AsyncEngine = _create_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência FastAPI que fornece uma `AsyncSession` por requisição.

    Padrão adotado (Fail Secure, Seção 1): em caso de exceção durante o
    processamento da requisição, a transação é revertida (`rollback`)
    explicitamente antes de propagar o erro, evitando que dados parciais
    ou inconsistentes sejam persistidos. Em caso de sucesso, o commit é
    responsabilidade explícita da camada de Service, não desta dependência
    — esta função apenas garante que a sessão é sempre fechada.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            logger.exception("Sessão de banco revertida devido a exceção não tratada.")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para uso de sessão fora do ciclo de requisição HTTP
    (ex: scripts administrativos, jobs agendados, testes).

    Diferente de `get_db_session`, este helper realiza commit automático
    ao final do bloco `with`, se nenhuma exceção for levantada.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """
    Libera todas as conexões do pool do engine.

    Deve ser chamado no evento de `shutdown` da aplicação (`app/main.py`,
    Etapa 8), garantindo encerramento limpo das conexões com o PostgreSQL.
    """
    await engine.dispose()
    logger.info("Engine do banco de dados finalizado.")
