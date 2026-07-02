"""
Handler de domínio para emissão e validação de JWTs de todos os tipos
usados pelo serviço (access, refresh, e-mail de confirmação, reset de
senha, desafio de MFA).

Camada de domínio de segurança sobre `app/core/security.py` — conhece as
regras de "quanto tempo cada tipo de token dura" e "qual claim `type`
cada um carrega".

Nota de decisão: este módulo importa e levanta diretamente as exceções
de `app/exceptions/auth_exceptions.py` (`InvalidTokenError`,
`TokenExpiredError`, `TokenTypeMismatchError`) em vez de definir sua
própria hierarquia paralela — evita ter dois conjuntos de exceções com
o mesmo nome (um "de segurança", outro "de domínio") que precisariam
ser traduzidos um para o outro em todo lugar que decodifica um token.
`app/exceptions/` não depende de `fastapi`/`Request` (ver
`base_exception.py`), então importá-lo aqui não quebra a regra de
"security nunca lança exceções HTTP" — a tradução para HTTP continua
acontecendo exclusivamente em `exception_handlers.py`.
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
)
from app.core.security import TokenExpiredError as _CoreTokenExpiredError
from app.core.security import (
    compute_expiry,
    decode_jwt,
    encode_jwt,
    hash_opaque_token,
    utcnow,
)
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
    """Fachada de emissão/validação de JWT usada pela camada de `services`."""

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
        """Emite um access token de curta duração (`ACCESS_TOKEN_EXPIRE_MINUTES`)."""
        ttl = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return cls._issue(TokenType.ACCESS, user_id, ttl, session_id=session_id)

    @classmethod
    def create_refresh_token(
        cls, user_id: uuid.UUID, *, session_id: uuid.UUID | None = None
    ) -> IssuedToken:
        """Emite um refresh token de longa duração (`REFRESH_TOKEN_EXPIRE_DAYS`)."""
        ttl = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return cls._issue(TokenType.REFRESH, user_id, ttl, session_id=session_id)

    @classmethod
    def create_email_confirmation_token(cls, user_id: uuid.UUID) -> IssuedToken:
        """Emite um token de uso único para `POST /auth/email/confirm`."""
        ttl = timedelta(hours=settings.EMAIL_TOKEN_EXPIRE_HOURS)
        return cls._issue(TokenType.EMAIL_CONFIRMATION, user_id, ttl)

    @classmethod
    def create_password_reset_token(cls, user_id: uuid.UUID) -> IssuedToken:
        """Emite um token de uso único para `POST /auth/password/reset`."""
        ttl = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        return cls._issue(TokenType.PASSWORD_RESET, user_id, ttl)

    @classmethod
    def create_mfa_challenge_token(cls, user_id: uuid.UUID) -> IssuedToken:
        """
        Emite o `challenge_token` de curta duração retornado por
        `MFAChallengeResponse` após um login com senha correta, mas
        pendente de verificação do código MFA.
        """
        ttl = timedelta(seconds=settings.MFA_CODE_VALID_SECONDS * 10)
        return cls._issue(TokenType.MFA_CHALLENGE, user_id, ttl)

    @staticmethod
    def decode(token: str, *, expected_type: TokenType) -> TokenPayload:
        """
        Decodifica um JWT e valida que seu `type` corresponde ao esperado
        pelo endpoint que o está consumindo.

        Levanta `TokenExpiredError` se expirado, `InvalidTokenError` se
        malformado/assinatura inválida, ou `TokenTypeMismatchError` se o
        tipo não corresponder — todas de `app.exceptions.auth_exceptions`,
        já prontas para serem propagadas até `exception_handlers.py`.
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
        """Calcula o hash de armazenamento de um refresh token (nunca o texto puro)."""
        return hash_opaque_token(raw_token)
