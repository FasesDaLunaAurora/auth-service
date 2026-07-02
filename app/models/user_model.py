"""
Entidade `User` (SQLAlchemy 2.x, estilo `Mapped`/`mapped_column`).

Regra de camada: este módulo contém APENAS o mapeamento ORM e validações
triviais de integridade (ex: normalização de e-mail). Nenhuma regra de
negócio (política de bloqueio, força de senha, etc.) vive aqui — isso é
responsabilidade de `app/services/user_service.py` e
`app/services/auth_service.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    # Import só avaliado por type checkers (Mypy) — evita import circular
    # em runtime entre `user_model`, `role_model`, `refresh_token_model` e
    # `session_model`.
    from app.models.refresh_token_model import RefreshToken
    from app.models.role_model import Role
    from app.models.session_model import Session


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Usuário do sistema.

    A exclusão de um `User` é sempre lógica (`deleted_at`, via
    `SoftDeleteMixin`) — nunca um `DELETE` físico, para preservar
    integridade referencial de auditoria, sessões e refresh tokens
    históricos.
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
    #
    # Nota de decisão (Etapa 6): a Seção 5 (modelagem de dados) NÃO lista
    # nenhum campo de MFA na tabela `User`, mas a Seção 6 define os
    # endpoints `POST /auth/mfa/enable` e `POST /auth/mfa/verify` como
    # parte obrigatória do contrato da API — logicamente impossível de
    # implementar sem persistir o secret TOTP e uma flag de "MFA ativo"
    # em algum lugar. Adiciono os dois campos abaixo ao model já gerado
    # na Etapa 2, já que este é um gap real da especificação, não uma
    # preferência de design.
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)

    # --- Relacionamentos ---
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """
        Normaliza o e-mail (lowercase + strip) antes de persistir.

        Esta é uma validação trivial de integridade de dados (permitida
        na camada `models` pela Seção 3), não uma regra de negócio —
        regras como "e-mail já cadastrado" continuam em `user_service`.
        """
        if not value or "@" not in value:
            raise ValueError("E-mail inválido.")
        return value.strip().lower()

    @property
    def is_locked(self) -> bool:
        """Indica se a conta está atualmente bloqueada por força bruta.

        Exposta como propriedade de conveniência; a decisão de *quando*
        bloquear/desbloquear permanece em `auth_service`.
        """
        return self.locked_until is not None and self.locked_until > datetime.now(timezone.utc)

    def __repr__(self) -> str:  # pragma: no cover - apenas debug
        return f"<User id={self.id} email={self.email!r}>"
