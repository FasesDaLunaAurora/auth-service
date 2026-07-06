"""
Gerencia a emissão e validação de JWTs (acesso, refresh, e-mail, reset e MFA).
Controla o tempo de expiração e o tipo de cada token com base no `app/core/security.py`.

Nota: Usa direto as exceções de `app/exceptions/auth_exceptions.py` para evitar
erros duplicados. Como essas exceções não dependem do FastAPI, o isolamento
é mantido, este módulo lança apenas erros de domínio, e a conversão para
HTTP fica por conta do `exception_handlers.py`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.constants import TokenType
from app.core.security import (
    TokenDecodeError,
    TokenEncodeError,
    compute_expiry,
    decode_jwt,
    encode_jwt,
    hash_opaque_token,
    utcnow,
)
from app.core.security import TokenExpiredError as _CoreTokenExpiredError
from app.exceptions.auth_exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    TokenTypeMismatchError,
)
from app.schemas.token_schema import TokenPayload

__all__ = [
    "JWTHandler",
    "IssuedToken",
    "InvalidTokenError",
    "TokenExpiredError",
    "TokenTypeMismatchError",
]


@dataclass(frozen=True, slots=True)
class IssuedToken:
    """Estrutura simples de retorno de emissão de token (não é um schema de API)."""

    token: str
    jti: uuid.UUID
    expires_at: datetime


class JWTHandler:
    """Interface para emissão e validação de JWT usada pelos services."""

    @staticmethod
    def _issue(
        token_type: TokenType,
        subject: uuid.UUID,
        ttl: timedelta,
        *,
        session_id: uuid.UUID | None = None,
    ) -> IssuedToken:
        jti = uuid.uuid4()
        issued_at = utcnow()
        expires_at = compute_expiry(ttl)
        claims = {
            "sub": str(subject),
            "type": token_type.value,
            "jti": str(jti),
            "sid": str(session_id) if session_id is not None else None,
            "iat": issued_at,
            "exp": expires_at,
            "iss": settings.JWT_ISSUER,
        }
        try:
            token = encode_jwt(claims)
        except TokenEncodeError as exc:
            raise InvalidTokenError("Não foi possível emitir o token.") from exc
        return IssuedToken(token=token, jti=jti, expires_at=expires_at)

    @classmethod
    def create_access_token(
        cls, user_id: uuid.UUID, *, session_id: uuid.UUID | None = None
    ) -> IssuedToken:
        """Gera um access token de curta duração (`ACCESS_TOKEN_EXPIRE_MINUTES`)."""
        ttl = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return cls._issue(TokenType.ACCESS, user_id, ttl, session_id=session_id)

    @classmethod
    def create_refresh_token(
        cls, user_id: uuid.UUID, *, session_id: uuid.UUID | None = None
    ) -> IssuedToken:
        """Gera um refresh token de longa duração (`REFRESH_TOKEN_EXPIRE_DAYS`)."""
        ttl = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return cls._issue(TokenType.REFRESH, user_id, ttl, session_id=session_id)

    @classmethod
    def create_email_confirmation_token(cls, user_id: uuid.UUID) -> IssuedToken:
        """Gera um token de uso único para `POST /auth/email/confirm`."""
        ttl = timedelta(hours=settings.EMAIL_TOKEN_EXPIRE_HOURS)
        return cls._issue(TokenType.EMAIL_CONFIRMATION, user_id, ttl)

    @classmethod
    def create_password_reset_token(cls, user_id: uuid.UUID) -> IssuedToken:
        """Gera um token de uso único para `POST /auth/password/reset`."""
        ttl = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        return cls._issue(TokenType.PASSWORD_RESET, user_id, ttl)

    @classmethod
    def create_mfa_challenge_token(cls, user_id: uuid.UUID) -> IssuedToken:
        """
        Gera o token temporário de MFA após o login com a senha correta.

        Esse token serve para validar o segundo fator (MFA) antes de liberar
        o acesso definitivo do usuário.
        """

        ttl = timedelta(seconds=settings.MFA_CODE_VALID_SECONDS * 10)
        return cls._issue(TokenType.MFA_CHALLENGE, user_id, ttl)

    @staticmethod
    def decode(token: str, *, expected_type: TokenType) -> TokenPayload:
        """
        Decodifica um JWT e valida se o tipo (`type`) é o esperado pela rota.

        Lança erros específicos do `app.exceptions.auth_exceptions` se o token estiver
        expirado, inválido ou com o tipo incorreto. O `exception_handlers.py` se encarrega
        de transformar esses erros em respostas HTTP.
        """

        try:
            raw_claims = decode_jwt(token)
        except _CoreTokenExpiredError as exc:
            raise TokenExpiredError() from exc
        except TokenDecodeError as exc:
            raise InvalidTokenError("Token inválido.") from exc

        try:
            payload = TokenPayload.model_validate(raw_claims)
        except Exception as exc:  # pydantic.ValidationError
            raise InvalidTokenError("Estrutura do token inválida.") from exc

        if payload.type != expected_type:
            raise TokenTypeMismatchError(
                f"Token do tipo '{payload.type.value}' não é aceito neste contexto "
                f"(esperado: '{expected_type.value}')."
            )
        return payload

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Gera o hash de um refresh token para salvar no banco (nunca salva o texto puro)."""
        return hash_opaque_token(raw_token)
