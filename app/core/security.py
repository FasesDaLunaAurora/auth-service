"""
Primitivas criptográficas de baixo nível: hashing de senha e
codificação/decodificação de JWT.

Nota de decisão de arquitetura: a árvore de pastas (Seção 4) lista tanto
`app/core/security.py` quanto um pacote `app/security/` com
`jwt_handler.py`, `password_handler.py`, `mfa_handler.py` e
`oauth2_handler.py`. O cronograma da Etapa 5 menciona apenas
`app/core/security.py`. Resolvo a sobreposição assim: **este arquivo**
concentra as primitivas puras e sem estado de negócio (chamadas de
biblioteca: `passlib`, `python-jose`, `hashlib`) — é o "motor"
criptográfico. Os módulos em `app/security/` (gerados a seguir, nesta
mesma etapa, por dependerem diretamente destas primitivas) são a camada
de domínio de segurança citada na tabela da Seção 3 (JWT, hashing,
MFA, OAuth2) que os `services` efetivamente importam. Isso evita
duplicar a configuração do `CryptContext`/`jose` em múltiplos arquivos.

Este módulo nunca acessa repositórios nem lança exceções HTTP — apenas
primitivas e suas próprias exceções de baixo nível.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


class TokenEncodeError(Exception):
    """Levantada quando a codificação de um JWT falha (erro de configuração/chave)."""


class TokenDecodeError(Exception):
    """
    Levantada quando um JWT não pode ser decodificado ou validado.

    Cobre assinatura inválida e token malformado — expiração é sinalizada
    separadamente por `TokenExpiredError` (subclasse desta), permitindo
    que a camada de domínio (`app/security/jwt_handler.py`) devolva
    mensagens/códigos de erro distintos para cada caso.
    """


class TokenExpiredError(TokenDecodeError):
    """Levantada especificamente quando a claim `exp` do JWT já expirou."""


# --- Hashing de senha ---
#
# `CryptContext` é configurado com os dois schemes permitidos pela Seção 2
# (`bcrypt` e `argon2`), com o scheme "primário" definido por
# `PASSWORD_HASH_SCHEME`. Manter ambos os schemes como "válidos para
# verificação" (não apenas para geração) permite migrar de scheme no
# futuro sem invalidar hashes já emitidos.
_password_context = CryptContext(
    schemes=["bcrypt", "argon2"],
    default=settings.PASSWORD_HASH_SCHEME,
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """Gera o hash de uma senha em texto puro usando o scheme configurado."""
    return _password_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica uma senha em texto puro contra um hash armazenado.

    Usa comparação em tempo constante internamente (garantida pelo
    próprio `passlib`), mitigando ataques de timing.
    """
    try:
        return _password_context.verify(plain_password, hashed_password)
    except ValueError:
        # Hash em formato desconhecido/corrompido — tratado como "não
        # confere", nunca propagado como erro 500 por esta camada.
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Indica se um hash existente deveria ser regenerado (scheme desatualizado)."""
    return _password_context.needs_update(hashed_password)


# --- JWT ---


def encode_jwt(claims: dict[str, Any]) -> str:
    """
    Codifica um dicionário de claims em um JWT assinado.

    Os valores de `claims` já devem estar em formatos serializáveis
    (datetimes são convertidos para timestamp Unix pela biblioteca
    `python-jose` automaticamente para as claims padrão `exp`/`iat`).
    """
    try:
        return jwt.encode(
            claims,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithm=settings.JWT_ALGORITHM,
        )
    except JWTError as exc:
        raise TokenEncodeError("Falha ao codificar o token JWT.") from exc


def decode_jwt(token: str) -> dict[str, Any]:
    """
    Decodifica e valida a assinatura/expiração de um JWT.

    Levanta `TokenDecodeError` para qualquer token invalido, expirado ou
    malformado — o chamador nunca deve precisar importar exceções da
    biblioteca `jose` diretamente.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True, "require_iat": True},
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token JWT expirado.") from exc
    except JWTError as exc:
        raise TokenDecodeError("Token JWT inválido.") from exc


def utcnow() -> datetime:
    """Horário atual em UTC — usado para calcular `iat`/`exp` de forma consistente."""
    return datetime.now(UTC)


def hash_opaque_token(raw_value: str) -> str:
    """
    Gera um hash determinístico (SHA-256) de um valor de token.

    Usado para armazenar refresh tokens e tokens de propósito único
    (reset de senha, confirmação de e-mail) sem nunca persistir o valor
    em texto puro (Seção 8). SHA-256 é apropriado aqui — diferente de
    senhas, tokens já possuem alta entropia própria (gerados por
    `secrets`/JWT assinado), então não é necessário um algoritmo lento
    como bcrypt/argon2 para esta finalidade.
    """
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def compute_expiry(delta: timedelta) -> datetime:
    """Calcula um timestamp de expiração absoluto a partir de agora + `delta`."""
    return utcnow() + delta
