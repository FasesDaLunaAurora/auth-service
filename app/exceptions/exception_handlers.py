"""
Tradução de exceções de domínio (e outras exceções conhecidas) para o
formato de erro HTTP padronizado da Seção 6:

```json
{"error": {"code": "...", "message": "...", "details": null}}
```

Este é o **único** lugar do projeto autorizado a construir
`JSONResponse`/conhecer `Request` a partir de uma exceção de domínio —
`services` e `repositories` nunca importam nada daqui. `register_exception_handlers`
é chamado uma única vez, em `app/main.py` (Etapa 8).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.constants import CORRELATION_ID_HEADER, ErrorCode
from app.core.logging import get_logger
from app.exceptions.base_exception import DomainException

logger = get_logger(__name__)


def _error_body(*, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def _correlation_id(request: Request) -> str | None:
    return request.headers.get(CORRELATION_ID_HEADER)


async def _handle_domain_exception(request: Request, exc: DomainException) -> JSONResponse:
    """
    Traduz qualquer `DomainException` (ou subclasse) para HTTP.

    O `status_code` e `error_code` já vêm definidos na própria classe da
    exceção (ver `base_exception.py`) — este handler só monta a resposta,
    sem precisar de um `if/elif` por tipo de exceção.
    """
    logger.info(
        "domain_exception_handled",
        exception_type=type(exc).__name__,
        error_code=exc.error_code.value,
        status_code=exc.status_code,
        correlation_id=_correlation_id(request),
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code=exc.error_code.value, message=exc.message, details=exc.details),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Traduz erros de validação do Pydantic/FastAPI (422) para o mesmo
    formato padronizado de erro, em vez do formato default do FastAPI.

    Nota de decisão: `exc.errors()` pode conter objetos não
    serializáveis em JSON puro dentro de `ctx` — por exemplo, quando um
    `@field_validator` customizado (ex: `PermissionCreate`) levanta um
    `ValueError`, o Pydantic inclui a exceção *crua* em
    `ctx["error"]`, e `json.dumps` não sabe serializar isso
    (`TypeError: Object of type ValueError is not JSON serializable`).
    `jsonable_encoder` (o mesmo usado internamente pelo FastAPI) resolve
    isso, convertendo para uma representação segura.
    """
    safe_errors = jsonable_encoder(exc.errors())
    logger.info(
        "request_validation_error",
        correlation_id=_correlation_id(request),
        path=str(request.url.path),
        errors=safe_errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Os dados enviados são inválidos.",
            details=safe_errors,
        ),
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Traduz `HTTPException`s "cruas" (ex: 404 de rota inexistente, 405
    método não permitido) que não passam pela camada de domínio — ainda
    assim, devem sair no mesmo formato padronizado de erro.
    """
    logger.info(
        "http_exception_handled",
        status_code=exc.status_code,
        correlation_id=_correlation_id(request),
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code=ErrorCode.VALIDATION_ERROR.value, message=str(exc.detail)),
    )


async def _handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Rede de segurança final (Fail Secure): qualquer exceção não prevista
    vira um 500 genérico, sem vazar detalhes internos (stack trace,
    mensagens de driver de banco, etc.) para o cliente. O detalhe
    completo vai apenas para o log estruturado do servidor.
    """
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        correlation_id=_correlation_id(request),
        path=str(request.url.path),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Ocorreu um erro interno. Tente novamente mais tarde.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers de exceção na instância do FastAPI (chamado em `main.py`)."""
    app.add_exception_handler(DomainException, _handle_domain_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_exception)
