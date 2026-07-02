"""
Exceções de domínio específicas de `User` (e, por composição, `Role`/
`Permission`, que não possuem regras de negócio complexas o bastante
para justificar arquivos próprios — reaproveitam `base_exception.py`).
"""

from __future__ import annotations

from app.core.constants import ErrorCode
from app.exceptions.base_exception import DomainException


class EmailAlreadyExistsError(DomainException):
    """Levantada em `POST /auth/register` quando o e-mail já está cadastrado."""

    error_code = ErrorCode.EMAIL_ALREADY_EXISTS
    default_message = "Este e-mail já está cadastrado."
    status_code = 409


class InvalidCurrentPasswordError(DomainException):
    """Levantada em `PATCH /users/me/password` quando `current_password` não confere."""

    error_code = ErrorCode.INVALID_CREDENTIALS
    default_message = "A senha atual informada está incorreta."
    status_code = 401


class UserAlreadyActiveError(DomainException):
    """Levantada em `POST /users/{id}/activate` quando o usuário já está ativo."""

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Este usuário já está ativo."
    status_code = 409


class UserAlreadyInactiveError(DomainException):
    """Levantada em `POST /users/{id}/deactivate` quando o usuário já está inativo."""

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Este usuário já está inativo."
    status_code = 409


class CannotDeactivateSelfError(DomainException):
    """
    Impede que um usuário desative ou exclua a própria conta através dos
    endpoints administrativos (`/users/{id}`), evitando que um
    administrador se tranque para fora do sistema acidentalmente.

    Regra de negócio adicional não pedida explicitamente pela
    especificação, mas alinhada às boas práticas de segurança citadas na
    Seção 1 — registrada no changelog.
    """

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Você não pode desativar ou excluir a própria conta por este endpoint."
    status_code = 409
