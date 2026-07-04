"""
Constantes globais do domínio.

Este módulo concentra valores fixos que não dependem de configuração de
ambiente (esses vivem em `core/config.py`). Mantê-los centralizados evita
"magic numbers/strings" espalhados pelas camadas de serviço, segurança e
middleware.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class TokenType(StrEnum):
    """Tipos de token emitidos pelo serviço de autenticação."""

    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_CONFIRMATION = "email_confirmation"
    PASSWORD_RESET = "password_reset"
    MFA_CHALLENGE = "mfa_challenge"


class AuditAction(StrEnum):
    """Ações auditáveis registradas pelo `audit_middleware` / services."""

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    LOGOUT_ALL = "LOGOUT_ALL"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    ROLE_ASSIGNED = "ROLE_ASSIGNED"
    ROLE_REVOKED = "ROLE_REVOKED"
    PERMISSION_ASSIGNED = "PERMISSION_ASSIGNED"
    PERMISSION_REVOKED = "PERMISSION_REVOKED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    TOKEN_REUSE_DETECTED = "TOKEN_REUSE_DETECTED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    MFA_ENABLED = "MFA_ENABLED"
    ACCESS_DENIED = "ACCESS_DENIED"


class ErrorCode(StrEnum):
    """
    Códigos de erro estáveis retornados no corpo padronizado de erro.

    Esses códigos são contrato público da API — não devem ser renomeados
    sem versionamento, pois clientes podem tomar decisões de UX baseados
    neles (ex: exibir "conta bloqueada" vs "credenciais inválidas").
    """

    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    ACCOUNT_NOT_VERIFIED = "ACCOUNT_NOT_VERIFIED"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    MFA_REQUIRED = "MFA_REQUIRED"
    MFA_INVALID_CODE = "MFA_INVALID_CODE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Permissões "seed" conhecidas pelo próprio código (usadas em decorators e
# testes). Permissões adicionais podem ser criadas dinamicamente via API,
# mas estas são consideradas estruturais ao domínio.
class PermissionCode:
    USER_LIST: Final[str] = "user:list"
    USER_READ: Final[str] = "user:read"
    USER_CREATE: Final[str] = "user:create"
    USER_UPDATE: Final[str] = "user:update"
    USER_DELETE: Final[str] = "user:delete"

    ROLE_LIST: Final[str] = "role:list"
    ROLE_READ: Final[str] = "role:read"
    ROLE_CREATE: Final[str] = "role:create"
    ROLE_UPDATE: Final[str] = "role:update"
    ROLE_DELETE: Final[str] = "role:delete"
    ROLE_ASSIGN: Final[str] = "role:assign"

    PERMISSION_LIST: Final[str] = "permission:list"
    PERMISSION_CREATE: Final[str] = "permission:create"
    PERMISSION_UPDATE: Final[str] = "permission:update"
    PERMISSION_DELETE: Final[str] = "permission:delete"
    PERMISSION_ASSIGN: Final[str] = "permission:assign"

    SESSION_LIST: Final[str] = "session:list"
    SESSION_REVOKE: Final[str] = "session:revoke"


# Cabeçalhos de segurança aplicados globalmente pelo middleware.
SECURITY_HEADERS: Final[dict[str, str]] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "X-Permitted-Cross-Domain-Policies": "none",
}

# Header usado para correlacionar requisições nos logs estruturados.
CORRELATION_ID_HEADER: Final[str] = "X-Request-ID"

# Mensagem genérica usada para respostas de autenticação, evitando
# enumeration attacks (não revelar se o e-mail existe ou não).
GENERIC_AUTH_ERROR_MESSAGE: Final[str] = "E-mail ou senha incorretos."
GENERIC_PASSWORD_RESET_MESSAGE: Final[str] = (
    "Se o e-mail informado estiver cadastrado, você receberá instruções para redefinição de senha."
)
