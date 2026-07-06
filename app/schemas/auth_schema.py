"""
Validadores (Schemas) para os fluxos de autenticação e sessões.

Centraliza os modelos de dados de entrada e saída das rotas de auth
e gerenciamento de dispositivos, mantendo a estrutura de arquivos
organizada e facilitando o reaproveitamento de campos de tokens.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.user_schema import UserCreate, validate_password_strength

# --- Registro ---


class RegisterRequest(UserCreate):
    """
    Dados de entrada para o cadastro de novos usuários.

    Inclui os campos de criação e adiciona a confirmação de senha,
    que serve exclusivamente para a validação inicial do formulário.
    """

    password_confirm: str = Field(..., min_length=1, max_length=128)

    @model_validator(mode="after")
    def _check_passwords_match(self) -> RegisterRequest:
        if self.password != self.password_confirm:
            raise ValueError("A senha e a confirmação de senha não coincidem.")
        return self


class RegisterResponse(BaseModel):
    """
    Resposta de cadastro de novos usuários.
    Não inclui tokens de acesso, pois o fluxo exige a confirmação do e-mail
    antes de permitir o primeiro login no sistema.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_verified: bool


# --- Login ---


class LoginRequest(BaseModel):
    """Payload de `POST /auth/login`."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


# --- Refresh ---


class RefreshRequest(BaseModel):
    """Payload de `POST /auth/refresh`."""

    refresh_token: str = Field(..., min_length=1)


# --- Logout ---


class LogoutRequest(BaseModel):
    """
    Dados de entrada para o logout do sistema.

    O `refresh_token` é opcional. Se for enviado, o sistema invalida esse
    token específico; caso contrário, encerra a sessão ativa do usuário.
    """

    refresh_token: str | None = None


# --- Recuperação de senha ---


class ForgotPasswordRequest(BaseModel):
    """Payload de `POST /auth/password/forgot`."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload de `POST /auth/password/reset`."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def _validate(self) -> ResetPasswordRequest:
        validate_password_strength(self.new_password)
        if self.new_password != self.new_password_confirm:
            raise ValueError("A nova senha e a confirmação não coincidem.")
        return self


# --- Confirmação de e-mail ---


class ConfirmEmailRequest(BaseModel):
    """Payload de `POST /auth/email/confirm`."""

    token: str = Field(..., min_length=1)


# --- MFA ---


class EnableMFAResponse(BaseModel):
    """Resposta de `POST /auth/mfa/enable`."""

    secret: str = Field(..., description="Secret TOTP, a ser exibido apenas uma vez ao usuário.")
    qr_code_uri: str = Field(
        ..., description="URI no formato 'otpauth://' para leitura por app autenticador."
    )


class VerifyMFARequest(BaseModel):
    """
    Dados de entrada para a verificação de MFA.

    O `challenge_token` é o token temporário gerado no login
    quando a conta tiver a autenticação em duas etapas ativada.
    """

    challenge_token: str = Field(..., min_length=1)
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


# --- Sessões  ---


class SessionRead(BaseModel):
    """Dados de retorno de uma sessão ativa exposta para o cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_info: str | None
    ip_address: str
    created_at: datetime
    last_active_at: datetime
    is_current: bool = Field(
        default=False,
        description="Preenchido pela camada de Service: indica a sessão da requisição atual.",
    )


class SessionListResponse(BaseModel):
    """Lista de sessões ativas retornada para o cliente."""

    items: list[SessionRead]
