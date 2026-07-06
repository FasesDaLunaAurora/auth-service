"""
Cliente Redis assíncrono para controle de rate limiting.
Este módulo gerencia a conexão com o Redis para alimentar os contadores
do middleware de limitação de requisições, centralizando o estado de acessos.
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """
    Retorna o cliente Redis assíncrono (Singleton).
    `decode_responses=True` faz o Redis já retornar texto, facilitando
    a leitura dos contadores de acesso.
    """

    return Redis.from_url(str(settings.REDIS_URL), decode_responses=True)


async def close_redis_client() -> None:
    """Fecha a conexão com o Redis no shutdown da aplicação."""
    client = get_redis_client()
    await client.aclose()
