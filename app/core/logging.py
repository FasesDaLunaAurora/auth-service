"""
Configuração de logging estruturado da aplicação.

Decisão de implementação: optamos por um formatter JSON próprio, sem
dependência externa (ex: `python-json-logger`), para manter o número de
dependências da Seção 2 restrito ao que foi especificado. O formatter
é aplicado em todos os handlers via `logging.config.dictConfig`.

Importante (Seção 8): este módulo NUNCA deve receber ou logar senhas,
tokens de acesso/refresh, secrets de MFA ou hashes de senha em texto
reconhecível. A camada de `services`/`security` é responsável por nunca
passar esses valores para o logger; este módulo apenas formata e emite.
"""

from __future__ import annotations

import json
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

# Chaves que, se aparecerem nos `extra` de um log, são automaticamente
# redigidas antes da emissão — última linha de defesa contra logging
# acidental de dados sensíveis.
_SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "access_token",
    "refresh_token",
    "token",
    "secret",
    "mfa_secret",
    "authorization",
}


class JSONFormatter(logging.Formatter):
    """Formata cada registro de log como uma linha JSON estruturada."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Campos extras (ex: request_id, user_id) passados via `extra=`.
        reserved = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
            "message",
            "asctime",
        }
        for key, value in record.__dict__.items():
            if key in reserved:
                continue
            payload[key] = "[REDACTED]" if key.lower() in _SENSITIVE_KEYS else value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """Formatter legível para desenvolvimento local (`LOG_JSON=false`)."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )


def configure_logging() -> None:
    """
    Aplica a configuração de logging para todo o processo da aplicação.

    Deve ser chamada uma única vez, no startup (`app/main.py`), antes de
    qualquer outro módulo emitir logs.
    """
    formatter_cls = "app.core.logging.JSONFormatter" if settings.LOG_JSON else "app.core.logging.PlainFormatter"

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"()": formatter_cls},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
        },
        "loggers": {
            # Reduz verbosidade de bibliotecas de terceiros por padrão.
            "uvicorn.access": {"level": "WARNING", "propagate": True},
            "sqlalchemy.engine": {
                "level": "WARNING" if not settings.DATABASE_ECHO else "INFO",
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado, padronizando o ponto de acesso ao logging."""
    return logging.getLogger(name)
