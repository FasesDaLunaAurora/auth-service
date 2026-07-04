"""
Configuração de logging estruturado (JSON) via `structlog`.

Logs estruturados são exigidos pela Seção 8 da especificação (auditoria de
login, logout, alteração de senha, etc). Este módulo apenas configura o
*pipeline* de logging; os eventos de auditoria específicos são emitidos
pela camada de `services` / `middleware`, nunca aqui.

Regra crítica: nenhum processador deste pipeline deve nunca receber ou
propagar senhas, tokens de acesso/refresh, ou segredos em texto puro. O
processor `_scrub_sensitive_fields` existe exatamente para isso — é uma
rede de segurança, não uma licença para logar dados sensíveis
deliberadamente.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
import structlog.typing

from app.core.config import settings
from collections.abc import MutableMapping

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
    """Processor do structlog que redige campos sensíveis antes de emitir o log."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging() -> None:
    """
    Configura `structlog` + `logging` stdlib.

    Deve ser chamado uma única vez, no startup da aplicação
    (`app/main.py`), antes de qualquer outro módulo emitir logs.
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
    """Retorna um logger estruturado nomeado (usar `__name__` do módulo chamador)."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
