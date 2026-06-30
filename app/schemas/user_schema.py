"""
Schemas de usuário (Seção 6 — /api/v1/users).

Cobre:
  - GET /users/me, PATCH /users/me, PATCH /users/me/password
  - GET /users (paginado), GET /users/{id}
  - PATCH /users/{id}, DELETE /users/{id}
  - POST /users/{id}/activate, /deactivate

Regra de separação de camadas (Seção 1): nenhum schema deste módulo
importa ou expõe diretamente um modelo ORM (`User`). A conversão
ORM → Schema é feita via `model_validate(orm_instance)`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.auth_schema import _validate_password_strength
from app.schemas.base_schema import AppBaseModel, OrmBaseModel, PaginatedResponse


# ---------------------------------------------------------------------------
# Response schemas (leitura de dados de usuário)
# ---------------------------------------------------------------------------

class UserResponse(OrmBaseModel):
    """
    Representação pública de um usuário.

    Campos omitidos intencionalmente por segurança (Seção 8):
      - `hashed_password` — nunca exposto
      - `mfa_secret`      — nunca exposto
      - `deleted_at`      — detalhe interno de soft-delete
      - `failed_login_attempts`, `locked_until` — informações de segurança
        interna não expostas ao cliente comum (disponíveis para superuser
        via `UserAdminResponse` abaixo)
    """

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime


class UserAdminResponse(UserResponse):
    """
    Representação estendida de usuário, disponível apenas para superusuários.

    Expõe campos operacionais como `failed_login_attempts` e `locked_until`,
    necessários para suporte e auditoria.

    Decisão de implementação: separar `UserResponse` (público) de
    `UserAdminResponse` (admin) é uma aplicação do princípio de
    Need-to-Know e Least Privilege (Seção 8 — Security by Design).
    """

    failed_login_attempts: int
    locked_until: datetime | None
    deleted_at: datetime | None


class UserWithRolesResponse(UserResponse):
    """Usuário com seus papéis (roles) incluídos — usado em `GET /users/me`."""

    roles: list[RoleMinimalResponse] = []


# ---------------------------------------------------------------------------
# Request schemas (escrita de dados de usuário)
# ---------------------------------------------------------------------------

class UpdateProfileRequest(AppBaseModel):
    """Atualização de perfil próprio — PATCH /users/me."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, value: str | None) -> str | None:
        if value is not None and not value.replace(" ", "").isalpha():
            raise ValueError("O nome completo deve conter apenas letras e espaços.")
        return value


class UpdateUserRequest(AppBaseModel):
    """
    Atualização de usuário por administrador — PATCH /users/{id}.

    Permite alterar mais campos do que a auto-edição (`UpdateProfileRequest`),
    incluindo `is_active` e `is_verified`.
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None
    is_verified: bool | None = None

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, value: str | None) -> str | None:
        if value is not None and not value.replace(" ", "").isalpha():
            raise ValueError("O nome completo deve conter apenas letras e espaços.")
        return value


class ChangePasswordRequest(AppBaseModel):
    """Alteração de senha própria — PATCH /users/me/password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    def validate_passwords_match(self) -> None:
        """
        Validação de correspondência de senhas.

        Decisão de implementação: feita como método explícito (não via
        `model_validator`) para que o `UserService` possa chamá-la depois
        de verificar a senha atual — evitando ordem de validação ambígua
        quando `current_password` é inválida.
        """
        if self.new_password != self.confirm_password:
            raise ValueError("As senhas não coincidem.")

    def is_same_as_current(self) -> bool:
        """Verifica se a nova senha é igual à senha atual (não hasheada)."""
        return self.new_password == self.current_password


class ChangePasswordResponse(AppBaseModel):
    """Confirmação de alteração de senha."""

    message: str = "Senha alterada com sucesso."


# ---------------------------------------------------------------------------
# Listagem paginada
# ---------------------------------------------------------------------------

# Alias tipado para a listagem de usuários paginada.
UserListResponse = PaginatedResponse[UserResponse]


# ---------------------------------------------------------------------------
# Schemas de role mínimo (evita importação circular com role_schema.py)
# ---------------------------------------------------------------------------

class RoleMinimalResponse(OrmBaseModel):
    """Representação mínima de um Role, embutida em respostas de User."""

    id: uuid.UUID
    name: str
    description: str | None


# Atualiza forward references para `UserWithRolesResponse`.
UserWithRolesResponse.model_rebuild()
