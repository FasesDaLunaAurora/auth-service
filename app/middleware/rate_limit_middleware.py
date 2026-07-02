"""
Rate limiting global por IP nas rotas de autenticação (Seção 7/10).

Implementado como um "fixed window counter" no Redis: para cada IP, uma
chave `ratelimit:auth:{ip}:{janela}` é incrementada a cada requisição às
rotas de `/auth/*`; se o contador exceder `RATE_LIMIT_AUTH_REQUESTS`
dentro de `RATE_LIMIT_AUTH_WINDOW_SECONDS`, a requisição é rejeitada.

Este middleware nunca contém regra de negócio de domínio (Seção 3) — ele
apenas conta requisições e levanta `RateLimitExceededError`, uma exceção
de domínio genérica já traduzida para HTTP 429 por
`exception_handlers.py`.
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

# Prefixo de rota protegido por rate limiting — apenas autenticação, per
# a Seção 7 ("Rate limiting global por IP... aplicado nas rotas de
# autenticação"). Demais rotas não são limitadas por este middleware
# (proteção geral de infraestrutura, se necessária, fica a cargo de um
# API Gateway/WAF fora do escopo deste serviço).
_PROTECTED_PATH_PREFIX = f"{settings.API_V1_PREFIX}/auth"


def _client_ip(request: Request) -> str:
    """
    Extrai o IP do cliente, respeitando `X-Forwarded-For` quando presente
    (o serviço normalmente roda atrás de um proxy/load balancer).

    Usa apenas o primeiro IP da lista (o cliente original) — confiar em
    `X-Forwarded-For` pressupõe que o proxy à frente do serviço já
    sanitiza este header antes de repassá-lo, prática padrão de
    infraestrutura fora do escopo deste código.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting por IP, restrito às rotas de autenticação."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not request.url.path.startswith(_PROTECTED_PATH_PREFIX):
            return await call_next(request)

        client_ip = _client_ip(request)
        window = int(time.time() // settings.RATE_LIMIT_AUTH_WINDOW_SECONDS)
        redis_key = f"ratelimit:auth:{client_ip}:{window}"

        redis_client = get_redis_client()
        current_count = await redis_client.incr(redis_key)
        if current_count == 1:
            # Só define o TTL na primeira requisição da janela, evitando
            # resetar a expiração a cada incremento subsequente.
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
