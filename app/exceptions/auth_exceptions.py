"""
Exceções de domínio específicas do fluxo de autenticação e autorização.
"""

from __future__ import annotations

from app.core.constants import GENERIC_AUTH_ERROR_MESSAGE, ErrorCode
from app.exceptions.base_exception import DomainException


class InvalidCredentialsError(DomainException):
    """
    E-mail/senha incorretos, ou e-mail não cadastrado.

    A mensagem é deliberadamente genérica (Seção 8: "mensagens de erro
    de login não devem revelar se o e-mail existe") — usada tanto para
    'usuário não encontrado' quanto para 'senha incorreta'.
    """

    error_code = ErrorCode.INVALID_CREDENTIALS
    default_message = GENERIC_AUTH_ERROR_MESSAGE
    status_code = 401


class AccountLockedError(DomainException):
    """Conta temporariamente bloqueada por excesso de tentativas de login falhas."""

    error_code = ErrorCode.ACCOUNT_LOCKED
    default_message = (
        "Conta temporariamente bloqueada devido a múltiplas tentativas de login "
        "malsucedidas. Tente novamente mais tarde."
    )
    status_code = 423  # 423 Locked


class AccountInactiveError(DomainException):
    """Conta desativada (`is_active=False`) — bloqueia login e uso de tokens existentes."""

    error_code = ErrorCode.ACCOUNT_INACTIVE
    default_message = "Esta conta está desativada."
    status_code = 403


class AccountNotVerifiedError(DomainException):
    """Conta ainda não confirmou o e-mail (`is_verified=False`)."""

    error_code = ErrorCode.ACCOUNT_NOT_VERIFIED
    default_message = "É necessário confirmar seu e-mail antes de fazer login."
    status_code = 403


class InvalidTokenError(DomainException):
    """
    Token (access, refresh, reset, confirmação ou desafio MFA)
    inválido, malformado, com assinatura incorreta ou de tipo
    incompatível com o endpoint que o recebeu.
    """

    error_code = ErrorCode.TOKEN_INVALID
    default_message = "Token inválido."
    status_code = 401


class TokenTypeMismatchError(InvalidTokenError):
    """
    Token estruturalmente válido, porém de um `type` diferente do
    esperado pelo endpoint (ex: um `refresh_token` apresentado onde um
    `access_token` era esperado, ou vice-versa).

    Subclasse de `InvalidTokenError` — do ponto de vista do cliente da
    API, ambos retornam o mesmo `error_code`/status; a distinção de
    classe existe para quem consome esta exceção internamente
    (`app/security/jwt_handler.py`) poder logar a causa exata, se
    necessário.
    """

    default_message = "Tipo de token incompatível com esta operação."


class TokenExpiredError(DomainException):
    """Token estruturalmente válido, porém expirado."""

    error_code = ErrorCode.TOKEN_EXPIRED
    default_message = "Token expirado."
    status_code = 401


class TokenRevokedError(DomainException):
    """
    Refresh token já revogado foi reapresentado (reuso/replay).

    Quando esta exceção é levantada, o `auth_service` já revogou, como
    efeito colateral de segurança, **todas** as sessões do usuário
    (Seção 7) antes de propagar o erro.
    """

    error_code = ErrorCode.TOKEN_REVOKED
    default_message = (
        "Token de atualização inválido. Por segurança, todas as sessões foram encerradas."
    )
    status_code = 401


class MFARequiredError(DomainException):
    """Reservada para cenários em que uma rota exige MFA ativo e ele não está configurado."""

    error_code = ErrorCode.MFA_REQUIRED
    default_message = "Autenticação multifator é obrigatória para esta conta."
    status_code = 401


class InvalidMFACodeError(DomainException):
    """Código TOTP informado em `POST /auth/mfa/verify` é inválido ou expirado."""

    error_code = ErrorCode.MFA_INVALID_CODE
    default_message = "Código de autenticação multifator inválido."
    status_code = 401
