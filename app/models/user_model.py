"""
Modelo de Usuário.

Responsável apenas pelo mapeamento ORM e integridade dos dados (como a
normalização do e-mail). Regras de negócio como força de senha e bloqueios
ficam exclusivamente na camada de serviços.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    # Evita import circular em runtime (usado apenas por type checkers).

    from app.models.refresh_token_model import RefreshToken
    from app.models.role_model import Role
    from app.models.session_model import Session


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Usuário do sistema.

    A exclusão é sempre lógica (`deleted_at`), evitando o DELETE físico
    para preservar o histórico de auditoria, sessões e tokens.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    # --- Campos de MFA ---
    # O secret TOTP e a flag de ativação são obrigatórios para os fluxos de MFA da API.

    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)

    roles: Mapped[list[Role]] = relationship(
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """
        Normaliza o e-mail (caixa baixa e sem espaços) antes de salvar.

        Validação de integridade de dados feita diretamente no modelo.
        Validações de negócio (como e-mail duplicado) ficam nos services.
        """

        if not value or "@" not in value:
            raise ValueError("E-mail inválido.")
        return value.strip().lower()

    @property
    def is_locked(self) -> bool:
        """
        Indica se a conta está bloqueada por excesso de tentativas.
        Propriedade para consulta rápida. A lógica que define o bloqueio
        e o tempo de expiração fica exclusivamente no `auth_service`.
        """

        return self.locked_until is not None and self.locked_until > datetime.now(UTC)

    def __repr__(self) -> str:  # pragma: no cover - apenas debug
        return f"<User id={self.id} email={self.email!r}>"
