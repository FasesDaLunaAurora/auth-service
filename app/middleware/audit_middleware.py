"""
Auditoria de segurança (Seção 8): login, logout, alteração de senha,
criação/alteração/exclusão de usuário, alteração de permissões,
revogação de token, tentativas de acesso inválidas.

Abordagem: este middleware infere o evento de auditoria a partir de
**metadados de transporte** apenas (método HTTP, path normalizado,
status code) — nunca lê o corpo da requisição/resposta, então nunca tem
a oportunidade de logar senhas, tokens ou outros dados sensíveis
(reforçando, na prática, a regra da Seção 8 de nunca logar segredos em
texto puro). O `user_id` incluído no log de auditoria é extraído de
forma best-effort do access token no header `Authorization`, apenas
para fins de rastreabilidade — a validação "de verdade" do token
continua sendo feita por `api/dependencies/auth_dependency.py` (Etapa 8).
"""

from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.constants import AuditAction
from app.core.logging import get_logger
from app.core.security import TokenDecodeError, decode_jwt

logger = get_logger(__name__)

_UUID_SEGMENT = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

_PREFIX = settings.API_V1_PREFIX

# Nota: os paths de `roles/{id}/permissions` e `users/{id}/roles` abaixo
# são provisórios — o contrato exato dessas rotas de atribuição (Seção 6
# só diz "incluindo endpoints para atribuir/remover roles... e
# permissions...", sem fixar o path) será definido em
# `app/api/routes/role_routes.py` (Etapa 8). Se o path final divergir,
# esta tabela deve ser ajustada em conjunto.
_AUDIT_RULES: dict[tuple[str, str], tuple[AuditAction | None, AuditAction | None]] = {
    ("POST", f"{_PREFIX}/auth/register"): (AuditAction.USER_CREATED, None),
    ("POST", f"{_PREFIX}/auth/login"): (AuditAction.LOGIN_SUCCESS, AuditAction.LOGIN_FAILURE),
    ("POST", f"{_PREFIX}/auth/mfa/verify"): (
        AuditAction.LOGIN_SUCCESS,
        AuditAction.LOGIN_FAILURE,
    ),
    ("POST", f"{_PREFIX}/auth/logout"): (AuditAction.LOGOUT, None),
    ("POST", f"{_PREFIX}/auth/logout-all"): (AuditAction.LOGOUT_ALL, None),
    ("POST", f"{_PREFIX}/auth/refresh"): (AuditAction.TOKEN_REFRESHED, None),
    ("POST", f"{_PREFIX}/auth/password/forgot"): (
        AuditAction.PASSWORD_RESET_REQUESTED,
        None,
    ),
    ("POST", f"{_PREFIX}/auth/password/reset"): (
        AuditAction.PASSWORD_RESET_COMPLETED,
        None,
    ),
    ("POST", f"{_PREFIX}/auth/mfa/enable"): (AuditAction.MFA_ENABLED, None),
    ("PATCH", f"{_PREFIX}/users/me/password"): (AuditAction.PASSWORD_CHANGED, None),
    ("PATCH", f"{_PREFIX}/users/{{id}}"): (AuditAction.USER_UPDATED, None),
    ("DELETE", f"{_PREFIX}/users/{{id}}"): (AuditAction.USER_DELETED, None),
    ("POST", f"{_PREFIX}/users/{{id}}/activate"): (AuditAction.USER_ACTIVATED, None),
    ("POST", f"{_PREFIX}/users/{{id}}/deactivate"): (AuditAction.USER_DEACTIVATED, None),
    ("POST", f"{_PREFIX}/roles/{{id}}/permissions"): (
        AuditAction.PERMISSION_ASSIGNED,
        None,
    ),
    ("DELETE", f"{_PREFIX}/roles/{{id}}/permissions/{{id}}"): (
        AuditAction.PERMISSION_REVOKED,
        None,
    ),
    ("POST", f"{_PREFIX}/users/{{id}}/roles"): (AuditAction.ROLE_ASSIGNED, None),
    ("DELETE", f"{_PREFIX}/users/{{id}}/roles/{{id}}"): (AuditAction.ROLE_REVOKED, None),
}


def _normalize_path(path: str) -> str:
    """Substitui segmentos de UUID por `{id}`, para casar com `_AUDIT_RULES`."""
    return _UUID_SEGMENT.sub("{id}", path)


def _extract_user_id(request: Request) -> str | None:
    """
    Tenta extrair o `sub` (user id) do access token, apenas para
    enriquecer o log de auditoria — falhas de decodificação são
    silenciosas aqui, pois a validação real do token é feita pela
    camada de dependências (Etapa 8), não por este middleware.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        claims = decode_jwt(token)
        return claims.get("sub")
    except TokenDecodeError:
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware de auditoria de segurança, baseado em metadados de transporte."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        normalized_path = _normalize_path(request.url.path)
        rule = _AUDIT_RULES.get((request.method, normalized_path))

        action: AuditAction | None = None
        if rule is not None:
            success_action, failure_action = rule
            action = success_action if response.status_code < 400 else failure_action
        elif response.status_code == 403:
            # Fallback: qualquer 403 não coberto por uma regra específica
            # ainda é uma tentativa de acesso negado relevante (Seção 8).
            action = AuditAction.ACCESS_DENIED
        elif response.status_code == 423:
            action = AuditAction.ACCOUNT_LOCKED

        if action is not None:
            logger.info(
                "audit_event",
                audit_action=action.value,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                user_id=_extract_user_id(request),
                client_ip=request.client.host if request.client else "unknown",
            )

        return response
