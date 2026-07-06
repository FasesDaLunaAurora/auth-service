"""
Regras de negócio de gerenciamento de sessões (`/api/v1/sessions`).

Criado para respeitar a estrutura de pastas do projeto, que exige um service
para cada entidade com rotas CRUD ativas.
"""

from __future__ import annotations

import uuid

from app.exceptions.base_exception import PermissionDeniedError, ResourceNotFoundError
from app.models.session_model import Session
from app.repositories.session_repository import SessionRepository


class SessionService:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._sessions = session_repository

    async def list_active_sessions(self, user_id: uuid.UUID) -> list[Session]:
        """Lista as sessões ativas do usuário autenticado (`GET /sessions`)."""
        return await self._sessions.list_active_for_user(user_id)

    async def revoke_session(self, *, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        """
        Encerra uma sessão específica (`DELETE /sessions/{id}`).

        Valida se a sessão pertence ao usuário logado antes de excluí-la. Por ser uma
        validação de dono do recurso (e não de perfil de acesso), essa regra fica aqui
        no service. Qualquer usuário comum pode derrubar suas próprias sessões, mas
        nunca as de outras pessoas.
        """

        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise ResourceNotFoundError("Sessão")
        if session.user_id != user_id:
            raise PermissionDeniedError("Esta sessão não pertence ao usuário autenticado.")
        await self._sessions.revoke(session)
