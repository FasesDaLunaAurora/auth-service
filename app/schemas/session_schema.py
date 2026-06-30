"""
Schemas de Session (Seção 6 — /api/v1/sessions).

Cobre:
  - GET /sessions  — lista sessões ativas do usuário autenticado
  - DELETE /sessions/{id} — revoga uma sessão específica
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base_schema import AppBaseModel, OrmBaseModel


class SessionResponse(OrmBaseModel):
    """Representação pública de uma sessão de autenticação."""

    id: uuid.UUID
    device_info: str | None
    ip_address: str
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime | None
    revoked: bool

    @property
    def is_active(self) -> bool:
        from datetime import timezone
        if self.revoked:
            return False
        if self.expires_at is not None:
            return datetime.now(timezone.utc) < self.expires_at
        return True


class SessionListResponse(AppBaseModel):
    """Lista de sessões ativas do usuário autenticado."""

    sessions: list[SessionResponse]
    total: int


class RevokeSessionResponse(AppBaseModel):
    """Confirmação de revogação de sessão."""

    message: str = "Sessão revogada com sucesso."
    session_id: uuid.UUID
