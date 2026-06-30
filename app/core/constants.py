"""
Constantes globais da aplicação.

Centraliza valores fixos usados em múltiplas camadas (services, exceptions,
security) para evitar strings "mágicas" espalhadas pelo código.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """
    Códigos de erro estáveis e estruturados, usados no envelope de erro
    padronizado descrito na Seção 6 da especificação:

    {
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "...",
            "details": null
        }
    }

    Decisão de implementação: usar um Enum (str) garante que o `code`
    nunca diverge entre camadas por erro de digitação em string literal.
    """

    # Autenticação
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    ACCOUNT_NOT_VERIFIED = "ACCOUNT_NOT_VERIFIED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    REFRESH_TOKEN_REUSED = "REFRESH_TOKEN_REUSED"
    MFA_REQUIRED = "MFA_REQUIRED"
    MFA_INVALID_CODE = "MFA_INVALID_CODE"

    # Usuário
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    EMAIL_ALREADY_VERIFIED = "EMAIL_ALREADY_VERIFIED"
    WEAK_PASSWORD = "WEAK_PASSWORD"

    # Autorização
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
    PERMISSION_NOT_FOUND = "PERMISSION_NOT_FOUND"

    # Genéricos
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DefaultPermission(str, Enum):
    """
    Permissões padrão (`code`) referenciadas pelo contrato de rotas
    na Seção 6 (ex: `user:list`, `user:read`, `role:*`).
    """

    USER_LIST = "user:list"
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    ROLE_LIST = "role:list"
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_ASSIGN = "role:assign"

    PERMISSION_LIST = "permission:list"
    PERMISSION_READ = "permission:read"
    PERMISSION_CREATE = "permission:create"
    PERMISSION_UPDATE = "permission:update"
    PERMISSION_DELETE = "permission:delete"
    PERMISSION_ASSIGN = "permission:assign"


class TokenType(str, Enum):
    """Tipos de token JWT emitidos pelo serviço, usados no claim `type`."""

    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_CONFIRMATION = "email_confirmation"
    PASSWORD_RESET = "password_reset"


class AuditAction(str, Enum):
    """
    Ações de auditoria obrigatórias conforme Seção 8: login, logout,
    alteração de senha, criação/alteração/exclusão de usuário,
    alteração de permissões, revogação de token, tentativas inválidas.
    """

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
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
    TOKEN_REVOKED = "TOKEN_REVOKED"
    TOKEN_REUSE_DETECTED = "TOKEN_REUSE_DETECTED"
    ACCESS_DENIED = "ACCESS_DENIED"


# Cabeçalhos de segurança aplicados via middleware (Seção 8).
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Referrer-Policy": "no-referrer",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cache-Control": "no-store",
}

# Mensagem genérica usada para mitigar Enumeration Attacks (Seção 8):
# nunca revelar se um e-mail existe ou não na base.
GENERIC_AUTH_ERROR_MESSAGE = "E-mail ou senha incorretos."
GENERIC_PASSWORD_RESET_MESSAGE = (
    "Se o e-mail informado estiver cadastrado, enviaremos instruções de redefinição."
)
