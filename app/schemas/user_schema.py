"""
Contratos de entrada/saída para `User` (`/api/v1/users`).

A função `validate_password_strength` é definida aqui (não em
`auth_schema.py`) porque senha é, conceitualmente, um atributo de `User`
— ela é reimportada por `auth_schema.py` nos payloads de registro e
redefinição de senha, evitando duplicar a regra de formato em dois
arquivos.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.role_schema import RoleRead

_PASSWORD_MIN_LENGTH = 8
_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


def validate_password_strength(value: str) -> str:
    """
    Valida o *formato* mínimo de uma senha em texto puro recebida via API.

    Esta validação é de forma/entrada (permitida na camada `schemas`
    pela Seção 3) — ela roda antes do valor chegar à camada de `Service`,
    que é quem efetivamente faz o hashing (`password_handler.py`,
    Etapa 5). Nenhuma regra de negócio sobre políticas de senha
    corporativa (histórico, expiração, etc.) vive aqui.
    """
    if len(value) < _PASSWORD_MIN_LENGTH:
        raise ValueError(f"A senha deve ter ao menos {_PASSWORD_MIN_LENGTH} caracteres.")
    if not _HAS_LETTER.search(value) or not _HAS_DIGIT.search(value):
        raise ValueError("A senha deve conter ao menos uma letra e um número.")
    return value


class UserBase(BaseModel):
    """Campos públicos e compartilhados de um usuário."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    """
    Payload interno de criação de usuário.

    Não é exposto diretamente como rota própria (a especificação só
    define criação via `POST /auth/register` — Seção 6); este schema é
    reutilizado por `auth_schema.RegisterRequest` para não duplicar
    `email`/`full_name`/`password`.
    """

    password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserRead(UserBase):
    """Representação pública de um usuário, retornada por endpoints de leitura."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RoleRead] = Field(default_factory=list)


class UserUpdateMe(BaseModel):
    """Payload de `PATCH /users/me` — o próprio usuário só altera seu perfil básico."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)


class UserAdminUpdate(BaseModel):
    """
    Payload de `PATCH /users/{id}` — atualização administrativa.

    Não inclui `is_superuser` diretamente editável por este endpoint
    genérico: elevar privilégios de superusuário é sensível demais para
    ser um campo opcional silencioso em um PATCH — a especificação não
    define uma rota dedicada para isso, então optei por deixar essa
    elevação fora do escopo automático (decisão registrada no
    changelog); pode ser adicionada como rota explícita se necessário.
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    """Payload de `PATCH /users/me/password`."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)
    new_password_confirm: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_new_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def _check_passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password_confirm:
            raise ValueError("A nova senha e a confirmação não coincidem.")
        if self.new_password == self.current_password:
            raise ValueError("A nova senha deve ser diferente da senha atual.")
        return self


class UserListResponse(BaseModel):
    """Envelope de paginação para `GET /users`."""

    items: list[UserRead]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
