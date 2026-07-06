"""
Mapeamento de exceções de negócio para o formato HTTP padrão da API:

```json
{"error": {"code": "...", "message": "...", "details": null}}
```

Centraliza o tratamento de erros do app. As camadas de service e repository
apenas lançam as exceções, e este módulo converte em `JSONResponse`.
Deve ser registrado uma única vez no startup da aplicação (`main.py`).
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
    Converte qualquer `DomainException` para a resposta HTTP padrão.

    Usa o `status_code` e `error_code` definidos na própria classe,
    evitando blocos de `if/elif` para cada tipo de exceção.
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
    Converte erros de validação do Pydantic (422) para o formato padrão da API.
    Nota técnica: `exc.errors()` pode conter objetos não serializáveis em `ctx`
    (como exceções cruas de ValueError lançadas por @field_validator). O uso do
    `jsonable_encoder` resolve isso, limpando a estrutura antes de gerar a resposta.
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
    Converte exceções HTTP nativas para o formato padrão da API.
    Cobre cenários como rotas inexistentes (404) ou métodos não permitidos (405)
    que não chegam a passar pelas regras de negócio.
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
    Fallback para erros inesperados (500).
    Retorna um erro genérico para o cliente sem vazar dados sensíveis
    (como stack trace ou erros de banco), salvando o erro completo apenas nos logs.
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
    """Registra os handlers de exceção na aplicação FastAPI."""
    app.add_exception_handler(DomainException, _handle_domain_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_exception)
