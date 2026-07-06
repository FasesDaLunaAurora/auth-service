"""
Middlewares/Dependências de autenticação.

Extrai e valida o Bearer token do header para retornar o usuário autenticado.
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

# auto_error=True já barra com 403 se faltar o token, sem precisar validar no código.
_bearer_scheme = HTTPBearer(auto_error=True, description="Access token (JWT) do Auth Service.")


async def get_current_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer_scheme)],
) -> TokenPayload:
    """
    Decodifica e valida o token sem bater no banco de dados.

    Separado de `get_current_user` para que rotas que só precisam das claims
    do token (ex: logout) evitem uma consulta desnecessária.
    """

    return JWTHandler.decode(credentials.credentials, expected_type=TokenType.ACCESS)


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_current_token_payload)],
    user_repository: UserRepositoryDep,
) -> User:
    """
    Busca o usuário no banco usando os dados do token.

    Lança `InvalidTokenError` ou `AccountInactiveError` se o usuário sumiu ou
    foi desativado após a emissão do token. Ambas são falhas de autenticação,
    e não erros comuns de negócio (como 404 ou 403).
    """

    user = await user_repository.get_by_id(payload.sub)
    if user is None:
        raise InvalidTokenError("O usuário associado a este token não existe mais.")
    if not user.is_active:
        raise AccountInactiveError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTokenPayload = Annotated[TokenPayload, Depends(get_current_token_payload)]
