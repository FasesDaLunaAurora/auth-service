"""
Schemas de Token — representações internas de tokens JWT e refresh tokens.

Estes schemas NÃO são expostos diretamente como request/response da API
pública; são usados internamente pela camada `security/` e `services/`
para transportar claims validados entre funções, respeitando a regra de
tipagem forte (100% type hints, Seção 1).

Separação de responsabilidade:
  - `TokenPayload` — claims decodificados de qualquer token JWT emitido
  - `AccessTokenPayload` — claims específicos do access token
  - `RefreshTokenPayload` — claims específicos do refresh token
  - `SpecialTokenPayload` — claims de tokens de uso único (reset, confirmação)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.core.constants import TokenType
from app.schemas.base_schema import AppBaseModel


class TokenPayload(AppBaseModel):
    """
    Claims base presentes em todos os JWTs emitidos pelo serviço.

    Campos seguem nomenclatura padrão JWT (RFC 7519):
      - `sub` — subject (UUID do usuário como string)
      - `exp` — expiration time (Unix timestamp)
      - `iat` — issued at (Unix timestamp)
      - `jti` — JWT ID (UUID único, usado para blacklist no Redis)
      - `type` — tipo do token (claim customizado)
    """

    sub: str = Field(..., description="UUID do usuário (subject).")
    exp: datetime
    iat: datetime
    jti: str = Field(..., description="JWT ID único — chave de blacklist no Redis.")
    type: TokenType

    @property
    def user_id(self) -> uuid.UUID:
        """Converte `sub` (str) para `uuid.UUID` com segurança de tipo."""
        return uuid.UUID(self.sub)

    @property
    def is_expired(self) -> bool:
        from datetime import timezone
        return datetime.now(timezone.utc) >= self.exp


class AccessTokenPayload(TokenPayload):
    """
    Claims do access token (curta duração — padrão 15min).

    Inclui o conjunto de permissões do usuário no momento da emissão,
    embutidas no token para evitar uma consulta ao banco a cada requisição.

    Decisão de implementação: embutir permissões no token é um trade-off
    consciente — elimina latência de DB em cada request autenticado, mas
    significa que alterações de permissão só se refletem após a expiração
    do access token (15 min). Para revogação imediata, usamos a blacklist
    no Redis via `jti`.
    """

    type: TokenType = TokenType.ACCESS
    permissions: list[str] = Field(
        default_factory=list,
        description="Lista de códigos de permissão (ex: ['user:read', 'role:list']).",
    )
    is_superuser: bool = False


class RefreshTokenPayload(TokenPayload):
    """
    Claims do refresh token (longa duração — padrão 7 dias).

    Contém apenas o `sub` e o `session_id`, para minimizar a superfície
    de exposição em caso de vazamento. Não embute permissões.
    """

    type: TokenType = TokenType.REFRESH
    session_id: str = Field(..., description="UUID da Session associada a este refresh token.")

    @property
    def session_uuid(self) -> uuid.UUID:
        return uuid.UUID(self.session_id)


class SpecialTokenPayload(TokenPayload):
    """
    Claims de tokens de uso único (password reset, email confirmation).

    `purpose` reutiliza `TokenType` para distinguir os dois casos e
    impede reuso cross-purpose (ex: usar token de confirmação de e-mail
    como token de reset de senha).
    """

    type: TokenType  # EMAIL_CONFIRMATION ou PASSWORD_RESET
    email: str = Field(..., description="E-mail do usuário alvo — validação extra de vínculo.")


class TokenPairSchema(AppBaseModel):
    """
    Par access + refresh token, produzido internamente pelo `AuthService`
    e convertido para `TokenResponse` (schema público) na camada de API.
    """

    access_token: str
    refresh_token: str
    access_token_payload: AccessTokenPayload
    expires_in: int = Field(description="Segundos até expiração do access token.")
