"""
Injeção de dependências: sessão do banco, repositórios e services.

Garante o desacoplamento: este arquivo monta e entrega as instâncias prontas
para as rotas, mas não toca no banco. Toda leitura/escrita deve passar
obrigatoriamente pelos repositórios instanciados aqui.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.integrations.email_client import EmailClient
from app.repositories.permission_repository import PermissionRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService
from app.services.role_service import RoleService
from app.services.session_service import SessionService
from app.services.user_service import UserService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Alias para `get_db_session`, facilitando o uso com `Depends(get_db)`."""
    async for session in get_db_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# --- Repositórios ---


def get_user_repository(db: DBSession) -> UserRepository:
    return UserRepository(db)


def get_role_repository(db: DBSession) -> RoleRepository:
    return RoleRepository(db)


def get_permission_repository(db: DBSession) -> PermissionRepository:
    return PermissionRepository(db)


def get_refresh_token_repository(db: DBSession) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_session_repository(db: DBSession) -> SessionRepository:
    return SessionRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
RoleRepositoryDep = Annotated[RoleRepository, Depends(get_role_repository)]
PermissionRepositoryDep = Annotated[PermissionRepository, Depends(get_permission_repository)]
RefreshTokenRepositoryDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]
SessionRepositoryDep = Annotated[SessionRepository, Depends(get_session_repository)]


# --- Integrações ---


def get_email_client() -> EmailClient:
    """
    Instanciado por requisição. Não usa `lru_cache` porque o `EmailClient`
    não guarda estado. Cada envio abre sua própria conexão SMTP, então o
    custo de recriar é irrelevante e evita problemas de concorrência.
    """

    return EmailClient()


EmailClientDep = Annotated[EmailClient, Depends(get_email_client)]


# --- Services ---


def get_auth_service(
    user_repository: UserRepositoryDep,
    refresh_token_repository: RefreshTokenRepositoryDep,
    session_repository: SessionRepositoryDep,
    email_client: EmailClientDep,
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        session_repository=session_repository,
        email_client=email_client,
    )


def get_user_service(
    user_repository: UserRepositoryDep,
    refresh_token_repository: RefreshTokenRepositoryDep,
    session_repository: SessionRepositoryDep,
) -> UserService:
    return UserService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        session_repository=session_repository,
    )


def get_role_service(
    role_repository: RoleRepositoryDep,
    permission_repository: PermissionRepositoryDep,
    user_repository: UserRepositoryDep,
) -> RoleService:
    return RoleService(
        role_repository=role_repository,
        permission_repository=permission_repository,
        user_repository=user_repository,
    )


def get_permission_service(permission_repository: PermissionRepositoryDep) -> PermissionService:
    return PermissionService(permission_repository)


def get_session_service(session_repository: SessionRepositoryDep) -> SessionService:
    return SessionService(session_repository)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
