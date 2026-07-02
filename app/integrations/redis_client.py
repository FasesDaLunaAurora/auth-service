"""
Cliente Redis assíncrono, usado por `rate_limit_middleware.py` (Etapa 7)
para os contadores de rate limiting (Seção 7/10).

Nota de decisão: nenhuma etapa do cronograma menciona explicitamente
`redis_client.py`, mas a árvore de pastas (Seção 4) o exige e o
middleware de rate limiting depende diretamente dele — gerado agora pela
mesma razão dos repositórios/serviços "adiantados" nas Etapas 4 e 6.
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """
    Retorna um cliente Redis assíncrono, singleton por processo.

    `decode_responses=True` faz o cliente retornar `str` em vez de
    `bytes`, simplificando o código do middleware de rate limiting, que
    só lida com contadores inteiros serializados como texto.
    """
    return Redis.from_url(str(settings.REDIS_URL), decode_responses=True)


async def close_redis_client() -> None:
    """Fecha a conexão Redis. Chamado no shutdown da aplicação (`app/main.py`)."""
    client = get_redis_client()
    await client.aclose()
