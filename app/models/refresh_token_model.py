"""
Entidade `RefreshToken`.

O valor real do refresh token **nunca** é persistido — apenas seu hash
(`token_hash`), gerado por `app/security/jwt_handler.py` (Etapa 5) via
uma função de hash rápida e determinística (ex.: SHA-256), suficiente
para comparação de posse do token sem expor o segredo em caso de leak do
banco de dados.
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


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """
    Refresh token de longa duração, usado para rotação de Access Tokens.

    A coluna `created_at` é suficiente aqui (não há necessidade de
    `updated_at`/`TimestampMixin` completo) pois um refresh token nunca é
    "atualizado" — ele é revogado (flag `revoked`) e um novo é emitido em
    seu lugar, conforme o fluxo de rotação da Seção 7.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"
