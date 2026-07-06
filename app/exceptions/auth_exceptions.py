"""Exceções do fluxo de autenticação e autorização."""

from __future__ import annotations

from app.core.constants import GENERIC_AUTH_ERROR_MESSAGE, ErrorCode
from app.exceptions.base_exception import DomainException


class InvalidCredentialsError(DomainException):
    """
    Erro de credenciais inválidas.
    A mensagem é genérica para evitar que o sistema revele se o e-mail
    existe ou não no banco (proteção contra enumeration attacks).
    """

    error_code = ErrorCode.INVALID_CREDENTIALS
    default_message = GENERIC_AUTH_ERROR_MESSAGE
    status_code = 401


class AccountLockedError(DomainException):
    """Conta bloqueada por excesso de tentativas inválidas."""

    error_code = ErrorCode.ACCOUNT_LOCKED
    default_message = (
        "Conta temporariamente bloqueada devido a múltiplas tentativas de login "
        "malsucedidas. Tente novamente mais tarde."
    )
    status_code = 423


class AccountInactiveError(DomainException):
    """Conta desativada: bloqueia novos logins e invalida os tokens ativos."""

    error_code = ErrorCode.ACCOUNT_INACTIVE
    default_message = "Esta conta está desativada."
    status_code = 403


class AccountNotVerifiedError(DomainException):
    """Conta com e-mail pendente de confirmação."""

    error_code = ErrorCode.ACCOUNT_NOT_VERIFIED
    default_message = "É necessário confirmar seu e-mail antes de fazer login."
    status_code = 403


class InvalidTokenError(DomainException):
    """
    Token inválido, malformado, com assinatura incorreta ou tipo incompatível.
    """

    error_code = ErrorCode.TOKEN_INVALID
    default_message = "Token inválido."
    status_code = 401


class TokenTypeMismatchError(InvalidTokenError):
    """
    Token com tipo diferente do esperado pelo endpoint.
    Subclasse de `InvalidTokenError`. O cliente da API recebe o mesmo código
    de erro, mas a distinção interna serve para gerar logs mais específicos.
    """

    default_message = "Tipo de token incompatível com esta operação."


class TokenExpiredError(DomainException):
    """Token expirado."""

    error_code = ErrorCode.TOKEN_EXPIRED
    default_message = "Token expirado."
    status_code = 401


class TokenRevokedError(DomainException):
    """
    Tentativa de reuso de um Refresh Token já revogado (Replay Attack).
    Quando este erro ocorre, todas as sessões ativas do usuário são derrubadas
    imediatamente como medida preventiva de segurança.
    """

    error_code = ErrorCode.TOKEN_REVOKED
    default_message = (
        "Token de atualização inválido. Por segurança, todas as sessões foram encerradas."
    )
    status_code = 401


class MFARequiredError(DomainException):
    """Lançada quando a rota exige MFA, mas ele não está configurado."""

    error_code = ErrorCode.MFA_REQUIRED
    default_message = "Autenticação multifator é obrigatória para esta conta."
    status_code = 401


class InvalidMFACodeError(DomainException):
    """Código TOTP inválido ou expirado."""

    error_code = ErrorCode.MFA_INVALID_CODE
    default_message = "Código de autenticação multifator inválido."
    status_code = 401
