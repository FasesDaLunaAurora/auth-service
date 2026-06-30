"""
Modelo de dados da entidade `User`.

Implementa todos os campos exigidos pela Seção 5 da especificação,
incluindo: bloqueio por força bruta (`failed_login_attempts`, `locked_until`),
exclusão lógica (`deleted_at`), verificação de e-mail e flag de superusuário.

Relacionamentos N:M com `Role` são feitos via tabela associativa `user_roles`,
definida neste módulo pois é dependente do ciclo de vida de `User`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, _utcnow

# ---------------------------------------------------------------------------
# Tabela associativa user_roles (Seção 5)
# ---------------------------------------------------------------------------
# Decisão de implementação: definimos a tabela associativa aqui (próxima
# à entidade dominante — User) em vez de criar um modelo separado. Como
# não há colunas extras na associação, uma `Table` plana é suficiente e
# mais simples que um modelo intermediário completo.
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Entidade principal de usuário.

    Campos além da Seção 5 não foram adicionados para evitar desvio
    de escopo. Todos os campos da spec estão presentes.
    """

    __tablename__ = "users"

    # --- Identidade ---
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # --- Flags de estado ---
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # --- Proteção contra força bruta (Seção 7) ---
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Exclusão lógica (soft delete, Seção 5) ---
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- MFA (Decisão de implementação) ---
    # A spec exige endpoints `/auth/mfa/enable` e `/auth/mfa/verify`.
    # Para suportá-los, o usuário precisa armazenar o secret TOTP e um
    # flag indicando se MFA está habilitado. O secret é criptografado em
    # repouso na camada de service (não responsabilidade do modelo).
    mfa_secret: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # --- Relacionamentos ---
    roles: Mapped[list[Role]] = relationship(  # type: ignore[name-defined]
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(  # type: ignore[name-defined]
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    sessions: Mapped[list[Session]] = relationship(  # type: ignore[name-defined]
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"

    @property
    def is_locked(self) -> bool:
        """
        Retorna True se a conta está bloqueada no momento atual.

        Decisão de implementação: a verificação de bloqueio é feita aqui
        como propriedade de conveniência. A lógica de negócio de *bloquear*
        (setar `locked_until`) vive no `AuthService`, não neste modelo.
        """
        from datetime import timezone

        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    @property
    def is_deleted(self) -> bool:
        """Retorna True se o usuário foi marcado como excluído (soft delete)."""
        return self.deleted_at is not None


# Importações circulares resolvidas via strings nos `relationship` acima.
# Os modelos referenciados ("Role", "RefreshToken", "Session") são importados
# pelo pacote `app/models/__init__.py` antes do uso, garantindo que o mapper
# SQLAlchemy os resolva corretamente.
from app.models.role_model import Role  # noqa: E402, F401
from app.models.refresh_token_model import RefreshToken  # noqa: E402, F401
from app.models.session_model import Session  # noqa: E402, F401
