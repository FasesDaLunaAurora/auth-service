"""
Primitivas criptográficas de baixo nível: hashing de senhas e tokens JWT.

Este arquivo concentra as funções puras e sem estado (camada de biblioteca
como passlib e python-jose). Os módulos em `app/security/` encapsulam essas
funções para criar as regras de domínio que os services de fato usam.

Regra de arquitetura: este módulo não acessa o banco de dados nem lança
exceções HTTP — apenas lida com criptografia e erros de baixo nível.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


class TokenEncodeError(Exception):
    """Lançada quando a geração do JWT falha (erro de chave ou configuração)."""


class TokenDecodeError(Exception):
    """
    Lançada quando um JWT é inválido ou não pode ser decodificado.

    Cobre assinatura inválida e token malformado. Tokens expirados usam a
    subclasse `TokenExpiredError`, permitindo que o `jwt_handler.py`
    retorne mensagens e códigos de erro específicos para cada cenário.
    """


class TokenExpiredError(TokenDecodeError):
    """Lançada especificamente quando o JWT já expirou (claim `exp`)."""


# --- Hashing de Senha ---
#
# Configura o CryptContext com suporte a bcrypt e argon2. Manter ambos os
# schemes válidos para verificação permite que o sistema valide senhas antigas
# e migre de formato no futuro sem quebrar os hashes existentes.

_password_context = CryptContext(
    schemes=["bcrypt", "argon2"],
    default=settings.PASSWORD_HASH_SCHEME,
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """Gera o hash da senha usando o scheme configurado."""
    return str(_password_context.hash(plain_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Valida a senha contra o hash armazenado.

    Usa comparação em tempo constante (via passlib) para mitigar ataques de timing.
    """

    try:
        return bool(_password_context.verify(plain_password, hashed_password))
    except ValueError:
        # Hash inválido ou corrompido: retorna False em vez de estourar um erro 500.
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Verifica se o hash precisa ser atualizado (ex: scheme antigo)."""
    return bool(_password_context.needs_update(hashed_password))


# --- JWT ---


def encode_jwt(claims: dict[str, Any]) -> str:
    """
    Gera um token JWT assinado a partir das claims passadas.
    A lib `python-jose` converte automaticamente campos de data
    (como `exp` e `iat`) para timestamp Unix durante a geração.
    """

    try:
        return str(
            jwt.encode(
                claims,
                settings.JWT_SECRET_KEY.get_secret_value(),
                algorithm=settings.JWT_ALGORITHM,
            )
        )
    except JWTError as exc:
        raise TokenEncodeError("Falha ao codificar o token JWT.") from exc


def decode_jwt(token: str) -> dict[str, Any]:
    """
    Decodifica e valida a assinatura e expiração do JWT.

    Lança `TokenDecodeError` se o token for inválido, expirado ou malformado.
    Isso evita que o restante do código precise importar exceções da lib `jose`.
    """

    try:
        return dict(
            jwt.decode(
                token,
                settings.JWT_SECRET_KEY.get_secret_value(),
                algorithms=[settings.JWT_ALGORITHM],
                options={"require_exp": True, "require_iat": True},
            )
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token JWT expirado.") from exc
    except JWTError as exc:
        raise TokenDecodeError("Token JWT inválido.") from exc


def utcnow() -> datetime:
    """Horário atual em UTC para calcular `iat`/`exp`."""
    return datetime.now(UTC)


def hash_opaque_token(raw_value: str) -> str:
    """
    Gera um hash SHA-256 determinístico de um token.

    Usado para persistir refresh tokens ou tokens de uso único (reset de senha,
    confirmação de e-mail) com segurança, sem salvar o valor limpo no banco.

    Como esses tokens já possuem alta entropia nativa (gerados via secrets/JWT),
    o SHA-256 é ideal aqui. Dispensa algoritmos lentos como bcrypt ou argon2,
    que são necessários apenas para senhas.
    """

    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def compute_expiry(delta: timedelta) -> datetime:
    """Calcula o timestamp de expiração somando o `delta` ao horário atual."""
    return utcnow() + delta
