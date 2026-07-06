"""
Schemas de entrada e saída para as rotas de usuários (`/api/v1/users`).

A função `validate_password_strength` fica aqui porque a senha é um
atributo do usuário. O `auth_schema.py` reimporta essa função para os
payloads de cadastro e reset de senha, evitando duplicar a regra de
validação. Nunca deve existir um módulo `utils`, tudo deve estar dentro
de um schema ou função específico.
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
    Valida o formato mínimo de uma senha em texto puro enviada para a API.

    Essa é uma checagem de entrada (camada schemas), rodando antes do valor
    chegar na camada Service. O hash da senha em si acontece depois no
    `password_handler.py`. Regras de negócio complexas (como histórico ou
    expiração) não entram aqui.
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
    Payload interno para criação de usuário.

    Não é usado direto em uma rota própria, já que a criação acontece via
    `POST /auth/register`. Este schema serve para ser reaproveitado por
    `auth_schema.RegisterRequest`, evitando duplicar os campos `email`,
    `full_name` e `password`.
    """

    password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserRead(UserBase):
    """Aqui sim, temos os dados públicos do usuário retornados pelas rotas de leitura."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RoleRead] = Field(default_factory=list)


class UserUpdateMe(BaseModel):
    """Campos para o `PATCH /users/me`, onde o usuário edita o próprio perfil básico."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)


class UserAdminUpdate(BaseModel):
    """
    Campos do `PATCH /users/{id}` para atualização via admin.

    O campo `is_superuser` ficou de fora porque dar permissão de superusuário
    é algo muito crítico para rodar em um PATCH genérico. Como não há uma rota
    específica na especificação, deixei essa alteração de fora por enquanto
    (está anotado no changelog). Se precisar, dá para criar um endpoint só
    para isso depois.
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    """Campos para alteração de senha em `PATCH /users/me/password`."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)
    new_password_confirm: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_new_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def _check_passwords_match(self) -> ChangePasswordRequest:
        if self.new_password != self.new_password_confirm:
            raise ValueError("A nova senha e a confirmação não coincidem.")
        if self.new_password == self.current_password:
            raise ValueError("A nova senha deve ser diferente da senha atual.")
        return self


class UserListResponse(BaseModel):
    """Estrutura de paginação para o `GET /users`."""

    items: list[UserRead]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
