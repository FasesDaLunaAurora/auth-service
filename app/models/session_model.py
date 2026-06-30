"""
Modelo de dados da entidade `Session`.

Implementa todos os campos da Seção 5. Cada registro representa uma sessão
de dispositivo ativa de um usuário. Suporta os casos de uso:

- `GET /sessions` — listar sessões ativas (revoked=False, não expiradas)
- `DELETE /sessions/{id}` — revogar uma sessão específica
- `POST /auth/logout-all` — revogar todas as sessões do usuário
- Detecção de reuso de refresh token (Seção 7): revogação em massa via
  `user_id`, executada pelo `AuthService`.

Decisão de implementação: adicionamos `expires_at` (não explicitado na
Seção 5) para permitir limpeza automática de sessões antigas via job
ou query filtrada — alinhado à boa prática de não acumular registros
de sessão indefinidamente em produção.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, _utcnow


class Session(UUIDPrimaryKeyMixin, Base):
    """Sessão de autenticação associada a um usuário e um dispositivo."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Informações de contexto da sessão (Seção 5) ---
    device_info: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="User-Agent ou identificação do dispositivo do cliente",
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="IPv4 ou IPv6 (máx 45 chars para IPv6 completo com escopo)",
    )

    # --- Timestamps (Seção 5) ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # --- Decisão de implementação: expiração explícita da sessão ---
    # Permite consultar sessões "expiradas mas não revogadas" separadamente
    # de sessões "revogadas ativamente pelo usuário", facilitando auditoria.
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Estado (Seção 5) ---
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # --- Relacionamento ---
    user: Mapped[User] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="sessions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Session id={self.id} user_id={self.user_id} "
            f"ip={self.ip_address!r} revoked={self.revoked}>"
        )

    @property
    def is_active(self) -> bool:
        """
        Sessão ativa = não revogada e, se `expires_at` definido, não expirada.
        """
        from datetime import timezone

        if self.revoked:
            return False
        if self.expires_at is not None:
            return datetime.now(timezone.utc) < self.expires_at
        return True


from app.models.user_model import User  # noqa: E402, F401
