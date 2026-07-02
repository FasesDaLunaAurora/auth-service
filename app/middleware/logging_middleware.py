"""
Logging estruturado por requisição, correlação de requisições e
aplicação dos headers de segurança (Seção 8).

Nota de decisão: a Seção 8 diz que os headers de segurança devem ser
"aplicados via middleware", sem especificar qual — apliquei aqui, neste
middleware, já que ele já envolve toda resposta (`call_next`) para
medir duração e logar status, então é o ponto natural para também
injetar headers de resposta, sem precisar de um middleware extra não
previsto na árvore de pastas (Seção 4 só lista três arquivos em
`middleware/`).
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import CORRELATION_ID_HEADER, SECURITY_HEADERS
from app.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware de logging estruturado, correlação de requisições e security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())

        # `bind_contextvars` torna `correlation_id` presente em *todo*
        # log estruturado emitido durante o processamento desta
        # requisição (inclusive dentro de `services`/`repositories`),
        # sem precisar passar o valor manualmente por toda a call stack.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        client_ip = request.client.host if request.client else "unknown"
        start_time = time.perf_counter()

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers[CORRELATION_ID_HEADER] = correlation_id
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        return response
