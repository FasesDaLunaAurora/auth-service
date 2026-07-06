"""
Regras de negócio de gestão de usuários.
"""

from __future__ import annotations

import uuid

from app.core.security import utcnow
from app.exceptions.base_exception import ResourceNotFoundError
from app.exceptions.user_exceptions import (
    CannotDeactivateSelfError,
    InvalidCurrentPasswordError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
)
from app.models.user_model import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import ChangePasswordRequest, UserAdminUpdate, UserUpdateMe
from app.security.password_handler import PasswordHandler


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        session_repository: SessionRepository,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._sessions = session_repository

    async def get_by_id_or_raise(self, user_id: uuid.UUID) -> User:
        """Busca um usuário por ID e lança um erro caso não seja encontrado."""

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError("Usuário")
        return user

    async def update_me(self, current_user: User, payload: UserUpdateMe) -> User:
        """Atualiza os dados do perfil do próprio usuário logado (`PATCH /users/me`)."""

        if payload.full_name is not None:
            current_user.full_name = payload.full_name
        await self._users.update(current_user)
        return current_user

    async def change_password(self, current_user: User, payload: ChangePasswordRequest) -> None:
        """
        Altera a senha do próprio usuário (`PATCH /users/me/password`).

        Após a troca, encerra todas as sessões e cancela os tokens antigos.
        Fazemos isso por segurança para derrubar o acesso em outros dispositivos.
        """

        is_valid = PasswordHandler.verify(payload.current_password, current_user.hashed_password)
        if not is_valid:
            raise InvalidCurrentPasswordError()

        current_user.hashed_password = PasswordHandler.hash(payload.new_password)
        await self._users.update(current_user)
        await self._refresh_tokens.revoke_all_for_user(current_user.id)
        await self._sessions.revoke_all_for_user(current_user.id)

    async def list_users(
        self, *, page: int, page_size: int, search: str | None
    ) -> tuple[list[User], int]:
        return await self._users.list_paginated(page=page, page_size=page_size, search=search)

    async def admin_update(self, user_id: uuid.UUID, payload: UserAdminUpdate) -> User:
        """Atualiza os dados de um usuário via admin (`PATCH /users/{id}`)."""
        user = await self.get_by_id_or_raise(user_id)
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.is_active is not None:
            user.is_active = payload.is_active
        await self._users.update(user)
        return user

    async def soft_delete(self, user_id: uuid.UUID, *, requesting_user_id: uuid.UUID) -> None:
        if user_id == requesting_user_id:
            raise CannotDeactivateSelfError()
        user = await self.get_by_id_or_raise(user_id)
        await self._users.soft_delete(user, deleted_at=utcnow())
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._sessions.revoke_all_for_user(user.id)

    async def activate(self, user_id: uuid.UUID) -> User:
        user = await self.get_by_id_or_raise(user_id)
        if user.is_active:
            raise UserAlreadyActiveError()
        user.is_active = True
        await self._users.update(user)
        return user

    async def deactivate(self, user_id: uuid.UUID, *, requesting_user_id: uuid.UUID) -> User:
        """
        Desativa uma conta de usuário (`POST /users/{id}/deactivate`).

        Também encerra todas as sessões e cancela os tokens ativos para
        garantir que a conta desativada não continue conectada.
        """

        if user_id == requesting_user_id:
            raise CannotDeactivateSelfError()
        user = await self.get_by_id_or_raise(user_id)
        if not user.is_active:
            raise UserAlreadyInactiveError()
        user.is_active = False
        await self._users.update(user)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._sessions.revoke_all_for_user(user.id)
        return user
