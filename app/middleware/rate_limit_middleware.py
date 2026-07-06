"""
Rate limiting por IP nas rotas de autenticação.

Bloqueia acessos excessivos usando o Redis para contar as requisições
em janelas de tempo fixas. Se o limite de IP for ultrapassado, barra a chamada.

Este middleware gerencia apenas o fluxo de tráfego. Ele dispara a exceção
`RateLimitExceededError` sem carregar regras de negócio aqui dentro.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.base_exception import RateLimitExceededError
from app.integrations.redis_client import get_redis_client

logger = get_logger(__name__)

# Filtra apenas rotas de autenticação. O controle de tráfego de outros
# endpoints fica sob responsabilidade do API Gateway ou WAF.

_PROTECTED_PATH_PREFIX = f"{settings.API_VERSION_PREFIX}/auth"


def _client_ip(request: Request) -> str:
    """
    Extrai o IP do cliente respeitando o cabeçalho `X-Forwarded-For`.

    Usa o primeiro IP da lista para identificar o cliente original.
    Assume que o proxy ou load balancer à frente já limpa este header.
    """

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting por IP para rotas de autenticação."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not request.url.path.startswith(_PROTECTED_PATH_PREFIX):
            return await call_next(request)

        client_ip = _client_ip(request)
        window = int(time.time() // settings.RATE_LIMIT_AUTH_WINDOW_SECONDS)
        redis_key = f"ratelimit:auth:{client_ip}:{window}"

        redis_client = get_redis_client()
        current_count = await redis_client.incr(redis_key)
        if current_count == 1:
            # Define a expiração apenas no primeiro acesso para não resetar a janela de tempo.

            await redis_client.expire(redis_key, settings.RATE_LIMIT_AUTH_WINDOW_SECONDS)

        if current_count > settings.RATE_LIMIT_AUTH_REQUESTS:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                count=current_count,
            )
            raise RateLimitExceededError()

        return await call_next(request)
