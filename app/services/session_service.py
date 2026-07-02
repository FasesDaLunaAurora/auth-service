"""
Regras de negócio de `Session` (`/api/v1/sessions`).

Ver nota de decisão em `permission_service.py` sobre módulos gerados
antecipadamente por dependência estrutural da árvore de pastas.
"""

from __future__ import annotations

import uuid

from app.exceptions.base_exception import PermissionDeniedError, ResourceNotFoundError
from app.models.session_model import Session
from app.repositories.session_repository import SessionRepository


class SessionService:
    """Orquestra as regras de negócio de `Session`."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._sessions = session_repository

    async def list_active_sessions(self, user_id: uuid.UUID) -> list[Session]:
        """Lista as sessões ativas do usuário autenticado (`GET /sessions`)."""
        return await self._sessions.list_active_for_user(user_id)

    async def revoke_session(self, *, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        """
        Revoga uma sessão específica (`DELETE /sessions/{id}`).

        Verifica que a sessão pertence ao usuário autenticado antes de
        revogá-la — esta é uma checagem de **posse do recurso**, não de
        RBAC (por isso vive aqui, no service, e não em
        `permission_dependency.py`): mesmo um usuário sem nenhuma role
        especial deve poder revogar suas próprias sessões, mas nunca as
        de terceiros.
        """
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise ResourceNotFoundError("Sessão")
        if session.user_id != user_id:
            raise PermissionDeniedError("Esta sessão não pertence ao usuário autenticado.")
        await self._sessions.revoke(session)
