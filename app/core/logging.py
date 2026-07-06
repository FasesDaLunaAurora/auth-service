"""
Configuração do logging estruturado (JSON) via `structlog`.

Este módulo configura o pipeline de logs. Os eventos de auditoria
são emitidos nos services/middlewares, e não aqui dentro.

Regra crítica: nunca logue senhas, tokens ou segredos em texto puro.
O processador `_scrub_sensitive_fields` serve como rede de segurança,
e não como licença para logar dados sensíveis de propósito.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog
import structlog.typing

from app.core.config import settings

_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "hashed_password",
        "new_password",
        "current_password",
        "access_token",
        "refresh_token",
        "token",
        "authorization",
        "secret",
        "jwt_secret_key",
        "mfa_code",
    }
)


def _scrub_sensitive_fields(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Processor do structlog que mascara campos sensíveis antes de gerar o log."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging() -> None:
    """
    Configura o `structlog` integrado com o `logging` nativo.

    Deve ser chamado uma única vez no startup da aplicação (`main.py`),
    antes que qualquer outro módulo gere logs.
    """

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _scrub_sensitive_fields,
    ]

    renderer: structlog.types.Processor
    if settings.LOG_JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.LOG_LEVEL)),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """Retorna um logger estruturado nomeado (passe `__name__` do módulo)."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
