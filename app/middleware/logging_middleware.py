"""
Middleware para logs estruturados, ID de correlação e headers de segurança.

Injeta as configurações de segurança e mede o tempo de resposta do app.
Centraliza essas ações em um único middleware para otimizar o fluxo de
resposta sem a necessidade de criar múltiplos arquivos no projeto.
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
    """Middleware de logs, ID de correlação e headers de segurança."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())

        # Vincula o ID de correlação ao contexto para que apareça
        # em todos os logs da requisição de forma automática.

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
