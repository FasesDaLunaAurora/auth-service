"""Rotas para gerenciamento de sessões."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.dependencies.auth_dependency import CurrentTokenPayload, CurrentUser
from app.api.dependencies.db_dependency import SessionServiceDep
from app.schemas.auth_schema import SessionListResponse, SessionRead

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get(
    "",
    response_model=SessionListResponse,
    summary="Lista sessões ativas do usuário autenticado",
)
async def list_sessions(
    current_user: CurrentUser,
    token_payload: CurrentTokenPayload,
    session_service: SessionServiceDep,
) -> SessionListResponse:
    sessions = await session_service.list_active_sessions(current_user.id)
    items = [
        SessionRead.model_validate(session).model_copy(
            update={"is_current": session.id == token_payload.sid}
        )
        for session in sessions
    ]
    return SessionListResponse(items=items)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga uma sessão específica",
)
async def revoke_session(
    session_id: uuid.UUID, current_user: CurrentUser, session_service: SessionServiceDep
) -> None:
    await session_service.revoke_session(user_id=current_user.id, session_id=session_id)
