"""
Modelo de dados da entidade `RefreshToken`.

Implementa todos os campos da Seção 5. Ponto crítico de segurança (Seção 8):
`token_hash` armazena **apenas o hash** do refresh token, nunca o valor em
texto puro. O hash é gerado na camada `security/` e jamais revertido a texto
puro — em caso de vazamento do banco, os tokens são inúteis sem o valor
original.

Suporta o mecanismo de detecção de reuso de token (token replay, Seção 7):
ao receber um refresh token já marcado como `revoked=True`, o `AuthService`
revoga **todas** as sessões do usuário.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, _utcnow


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """Refresh token persistido como hash, com suporte a revogação individual."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="SHA-256 do refresh token. NUNCA armazenar o token em texto puro.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # --- Relacionamento ---
    user: Mapped[User] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="refresh_tokens",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={self.revoked}>"
        )

    @property
    def is_expired(self) -> bool:
        """Verifica se o token já passou da data de expiração (UTC)."""
        from datetime import timezone

        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Token válido = não revogado e não expirado."""
        return not self.revoked and not self.is_expired


from app.models.user_model import User  # noqa: E402, F401
