"""
Contratos de entrada/saída para `/api/v1/auth` e `/api/v1/sessions`.

Nota de decisão de arquitetura: a Seção 4 da especificação lista
explicitamente apenas 5 arquivos em `app/schemas/` (`auth_schema.py`,
`user_schema.py`, `role_schema.py`, `permission_schema.py`,
`token_schema.py`) — não há `session_schema.py` na árvore de pastas,
apesar do cronograma de etapas mencionar "esquemas para Session". Como a
árvore de pastas (Seção 4) é a mais explícita e concreta das duas
instruções, resolvo a ambiguidade colocando os schemas de `Session` aqui
neste arquivo, já que sessões são criadas e revogadas como parte direta
do ciclo de vida de autenticação.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.user_schema import UserCreate, validate_password_strength

# --- Registro ---


class RegisterRequest(UserCreate):
    """
    Payload de `POST /auth/register`.

    Reutiliza `UserCreate` (email, full_name, password) e adiciona a
    confirmação de senha, que é uma preocupação exclusiva do formulário
    de registro (não da entidade `User` em si).
    """

    password_confirm: str = Field(..., min_length=1, max_length=128)

    @model_validator(mode="after")
    def _check_passwords_match(self) -> RegisterRequest:
        if self.password != self.password_confirm:
            raise ValueError("A senha e a confirmação de senha não coincidem.")
        return self


class RegisterResponse(BaseModel):
    """
    Resposta de `POST /auth/register`.

    Deliberadamente não retorna tokens de acesso — o fluxo exige
    confirmação de e-mail (`is_verified=False` até `POST
    /auth/email/confirm`) antes de permitir login, conforme os campos
    `is_verified`/`email/confirm` definidos nas Seções 5 e 6.
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
    Payload de `POST /auth/logout`.

    O `refresh_token` é opcional: se omitido, o serviço revoga a sessão
    associada ao access token atual (extraído do header
    `Authorization`); se informado, garante a revogação do par
    access/refresh específico usado naquele dispositivo.
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
    Payload de `POST /auth/mfa/verify`.

    O `challenge_token` é o token de curta duração retornado por
    `MFAChallengeResponse` (ver `token_schema.py`) após um `POST
    /auth/login` bem-sucedido em uma conta com MFA habilitado.
    """

    challenge_token: str = Field(..., min_length=1)
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


# --- Sessões (ver nota de decisão no topo do arquivo) ---


class SessionRead(BaseModel):
    """Representação pública de uma sessão ativa, retornada por `GET /sessions`."""

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
    """Envelope de resposta para `GET /sessions`."""

    items: list[SessionRead]
