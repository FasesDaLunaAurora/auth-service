"""
Schemas de autenticação (Seção 6 — /api/v1/auth).

Cobre todos os endpoints do grupo /auth:
  - register, login, refresh, logout, logout-all
  - password/forgot, password/reset
  - email/confirm
  - mfa/enable, mfa/verify

Regras de validação seguem OWASP e os requisitos de segurança da Seção 8.
"""

from __future__ import annotations

import re

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.config import settings
from app.schemas.base_schema import AppBaseModel


# ---------------------------------------------------------------------------
# Validators reutilizáveis
# ---------------------------------------------------------------------------

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).+$"
)


def _validate_password_strength(value: str) -> str:
    """
    Valida a força da senha conforme requisitos mínimos de segurança (Seção 8).

    Decisão de implementação: a spec não detalha a política de senha além
    de `PASSWORD_MIN_LENGTH`. Adoptamos como boa prática (alinhada ao OWASP
    Password Storage Cheat Sheet) exigir: mínimo de comprimento configurável,
    ao menos 1 maiúscula, 1 minúscula, 1 dígito e 1 caractere especial.
    """
    min_len = settings.PASSWORD_MIN_LENGTH
    if len(value) < min_len:
        raise ValueError(f"A senha deve ter pelo menos {min_len} caracteres.")
    if not _PASSWORD_RE.match(value):
        raise ValueError(
            "A senha deve conter ao menos uma letra maiúscula, uma minúscula, "
            "um número e um caractere especial."
        )
    return value


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class RegisterRequest(AppBaseModel):
    """Payload de cadastro de novo usuário — POST /auth/register."""

    email: EmailStr = Field(..., description="E-mail único do usuário.")
    password: str = Field(..., min_length=8, description="Senha em texto puro (será hasheada).")
    full_name: str = Field(..., min_length=2, max_length=255, description="Nome completo.")

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, value: str) -> str:
        if not value.replace(" ", "").isalpha():
            raise ValueError("O nome completo deve conter apenas letras e espaços.")
        return value


class RegisterResponse(AppBaseModel):
    """Resposta ao cadastro bem-sucedido."""

    message: str = "Cadastro realizado. Verifique seu e-mail para ativar a conta."
    email: EmailStr


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginRequest(AppBaseModel):
    """Payload de login — POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    mfa_code: str | None = Field(
        default=None,
        min_length=6,
        max_length=6,
        description="Código TOTP de 6 dígitos, obrigatório se MFA estiver ativado.",
    )


class TokenResponse(AppBaseModel):
    """
    Resposta de autenticação bem-sucedida (login e refresh).

    Retorna o par access + refresh token conforme o fluxo da Seção 7.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Segundos até a expiração do access token.",
    )


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

class RefreshRequest(AppBaseModel):
    """Payload de rotação de refresh token — POST /auth/refresh."""

    refresh_token: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutRequest(AppBaseModel):
    """
    Payload de logout — POST /auth/logout.

    O refresh token é necessário para revogá-lo no banco. O access token
    é invalidado via blacklist no Redis (TTL = tempo restante do token).
    """

    refresh_token: str = Field(..., min_length=1)


class LogoutResponse(AppBaseModel):
    """Confirmação de logout."""

    message: str = "Sessão encerrada com sucesso."


# ---------------------------------------------------------------------------
# Password — Forgot & Reset
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(AppBaseModel):
    """
    Solicitação de recuperação de senha — POST /auth/password/forgot.

    Decisão anti-enumeration (Seção 8): independentemente de o e-mail
    existir ou não, a resposta é sempre a mesma (`GENERIC_PASSWORD_RESET_MESSAGE`).
    """

    email: EmailStr


class ForgotPasswordResponse(AppBaseModel):
    """Resposta genérica de forgot-password (não revela se o e-mail existe)."""

    message: str


class ResetPasswordRequest(AppBaseModel):
    """Redefinição de senha via token — POST /auth/password/reset."""

    token: str = Field(..., min_length=1, description="Token de reset recebido por e-mail.")
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> ResetPasswordRequest:
        if self.new_password != self.confirm_password:
            raise ValueError("As senhas não coincidem.")
        return self


class ResetPasswordResponse(AppBaseModel):
    """Confirmação de redefinição de senha."""

    message: str = "Senha redefinida com sucesso."


# ---------------------------------------------------------------------------
# E-mail confirmation
# ---------------------------------------------------------------------------

class EmailConfirmRequest(AppBaseModel):
    """Confirmação de e-mail via token — POST /auth/email/confirm."""

    token: str = Field(..., min_length=1, description="Token de confirmação recebido por e-mail.")


class EmailConfirmResponse(AppBaseModel):
    """Confirmação de verificação de e-mail."""

    message: str = "E-mail verificado com sucesso."


# ---------------------------------------------------------------------------
# MFA — Enable & Verify
# ---------------------------------------------------------------------------

class MFAEnableResponse(AppBaseModel):
    """
    Resposta ao ativar MFA — POST /auth/mfa/enable.

    Retorna o secret TOTP e o URI otpauth:// para geração do QR code.
    O secret deve ser apresentado UMA única vez ao usuário; após isso
    apenas o hash é armazenado (Seção 8, Security by Design).

    Decisão de implementação: retornamos o `provisioning_uri` para que
    o cliente possa gerar o QR code no frontend sem depender do backend
    para renderizá-lo — seguro e sem tráfego desnecessário de imagem.
    """

    secret: str = Field(description="Secret TOTP em Base32. Mostrar apenas uma vez.")
    provisioning_uri: str = Field(description="URI otpauth:// para QR code.")
    message: str = "Escaneie o QR code no seu aplicativo autenticador e confirme com /auth/mfa/verify."


class MFAVerifyRequest(AppBaseModel):
    """Verificação de código MFA — POST /auth/mfa/verify."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="Código TOTP de 6 dígitos.")

    @field_validator("code")
    @classmethod
    def _only_digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("O código MFA deve conter apenas dígitos.")
        return value


class MFAVerifyResponse(AppBaseModel):
    """Resposta após verificação MFA bem-sucedida (parte do fluxo de login)."""

    message: str = "MFA verificado com sucesso."
