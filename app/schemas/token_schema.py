"""
Contratos relacionados a tokens (JWT de acesso/refresh).

Estes schemas são consumidos por `app/security/jwt_handler.py` (Etapa 5,
para tipar o payload decodificado) e por `app/schemas/auth_schema.py`
(para tipar as respostas de login/refresh).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import TokenType


class TokenResponse(BaseModel):
    """
    Corpo de resposta padrão para emissão/rotação de tokens.

    Usado por `POST /auth/login` (após autenticação completa, sem MFA
    pendente) e por `POST /auth/refresh`.
    """

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer", frozen=True)
    expires_in: int = Field(..., description="Segundos até a expiração do access_token.")


class TokenPayload(BaseModel):
    """
    Estrutura tipada do payload (claims) de um JWT emitido por este serviço.

    Não é exposta diretamente pela API — é usada internamente por
    `jwt_handler.py` para validar/desserializar claims de forma segura,
    em vez de acessar um `dict` cru em múltiplos pontos do código.
    """

    sub: uuid.UUID = Field(..., description="ID do usuário (subject).")
    type: TokenType
    jti: uuid.UUID = Field(..., description="Identificador único do token (JWT ID).")
    sid: uuid.UUID | None = Field(
        default=None,
        description="ID da Session de dispositivo associada (apenas em access/refresh tokens).",
    )
    iat: datetime
    exp: datetime
    iss: str | None = None


class MFAChallengeResponse(BaseModel):
    """
    Retornado por `POST /auth/login` quando o usuário tem MFA habilitado,
    em vez do par de tokens completo — o cliente deve then chamar
    `POST /auth/mfa/verify` com o `challenge_token` para concluir o login.
    """

    mfa_required: bool = Field(default=True, frozen=True)
    challenge_token: str = Field(
        ..., description="Token de curta duração (tipo MFA_CHALLENGE) para completar o login."
    )
