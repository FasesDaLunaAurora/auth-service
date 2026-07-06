"""Exceções de negócio para usuários, roles e permissões."""

from __future__ import annotations

from app.core.constants import ErrorCode
from app.exceptions.base_exception import DomainException


class EmailAlreadyExistsError(DomainException):
    """Lançada quando o e-mail informado já está cadastrado."""

    error_code = ErrorCode.EMAIL_ALREADY_EXISTS
    default_message = "Este e-mail já está cadastrado."
    status_code = 409


class InvalidCurrentPasswordError(DomainException):
    """Lançada quando a senha atual informada está incorreta."""

    error_code = ErrorCode.INVALID_CREDENTIALS
    default_message = "A senha atual informada está incorreta."
    status_code = 401


class UserAlreadyActiveError(DomainException):
    """Lançada se tentar ativar um usuário que já está ativo."""

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Este usuário já está ativo."
    status_code = 409


class UserAlreadyInactiveError(DomainException):
    """Lançada se tentar desativar um usuário que já está inativo."""

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Este usuário já está inativo."
    status_code = 409


class CannotDeactivateSelfError(DomainException):
    """
    Impede que um administrador desative ou exclua a própria conta.

    Garante que o usuário não se tranque para fora do sistema acidentalmente
    através dos endpoints de gerenciamento.
    """

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Você não pode desativar ou excluir a própria conta por este endpoint."
    status_code = 409
