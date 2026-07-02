"""
Dependências de autenticação: extraem e validam o access token do header
`Authorization: Bearer <token>` e resolvem o `User` autenticado.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies.db_dependency import UserRepositoryDep
from app.core.constants import TokenType
from app.exceptions.auth_exceptions import AccountInactiveError, InvalidTokenError
from app.models.user_model import User
from app.schemas.token_schema import TokenPayload
from app.security.jwt_handler import JWTHandler

# `auto_error=True` faz o FastAPI já retornar 403 automaticamente se o
# header `Authorization` estiver ausente, antes mesmo desta dependência
# ser chamada — simplifica o tratamento de "requisição sem token".
_bearer_scheme = HTTPBearer(auto_error=True, description="Access token (JWT) do Auth Service.")


async def get_current_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer_scheme)],
) -> TokenPayload:
    """
    Decodifica e valida o access token, sem ainda consultar o banco.

    Separado de `get_current_user` para que rotas que só precisam de
    dados do próprio token (ex: `sid` para logout) não paguem o custo de
    uma consulta ao usuário desnecessariamente.
    """
    return JWTHandler.decode(credentials.credentials, expected_type=TokenType.ACCESS)


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_current_token_payload)],
    user_repository: UserRepositoryDep,
) -> User:
    """
    Resolve o `User` autenticado a partir do access token.

    Levanta `InvalidTokenError` se o usuário referenciado pelo token não
    existir mais (ex: excluído após o token ter sido emitido) e
    `AccountInactiveError` se a conta foi desativada nesse meio-tempo —
    ambos os casos tratados como falha de autenticação, não 404/403
    "de negócio".
    """
    user = await user_repository.get_by_id(payload.sub)
    if user is None:
        raise InvalidTokenError("O usuário associado a este token não existe mais.")
    if not user.is_active:
        raise AccountInactiveError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTokenPayload = Annotated[TokenPayload, Depends(get_current_token_payload)]
