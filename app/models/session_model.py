"""
Entidade `Session`.

Representa uma sessão lógica de um usuário autenticado em um dispositivo
específico (não confundir com sessão de banco de dados). Cada login bem
sucedido cria uma `Session`; `GET /sessions` e `DELETE /sessions/{id}`
(Seção 6) operam sobre esta entidade.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from app.models.user_model import User


class Session(UUIDPrimaryKeyMixin, Base):
    """
    Sessão de dispositivo/cliente associada a um usuário.

    `last_active_at` é atualizado pela camada de serviço a cada uso
    válido do access token associado (não a cada requisição HTTP, para
    evitar overhead de escrita — decisão registrada no changelog).
    """

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_info: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)  # suporta IPv6
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session id={self.id} user_id={self.user_id} revoked={self.revoked}>"
