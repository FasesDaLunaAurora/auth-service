"""
Exceção de domínio base e exceções genéricas reutilizadas por múltiplos
domínios (`user`, `role`, `permission`, `session`).

Regra de camada (Seção 3): `services` levantam apenas estas exceções (ou
suas subclasses definidas em `auth_exceptions.py`/`user_exceptions.py`),
nunca `HTTPException`. A tradução para HTTP acontece exclusivamente em
`exception_handlers.py`, que lê o atributo `status_code` de cada exceção
— um dado simples, não uma dependência de `fastapi`/`Request`/`Response`
— para montar a resposta.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import ErrorCode


class DomainException(Exception):
    """
    Base de toda exceção de domínio da aplicação.

    Subclasses devem sobrescrever `error_code`, `default_message` e
    `status_code`. `details` é opcional e usado para contexto adicional
    não sensível (nunca deve conter senhas, tokens ou hashes).
    """

    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    default_message: str = "Ocorreu um erro inesperado."
    status_code: int = 500

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class ResourceNotFoundError(DomainException):
    """
    Recurso genérico não encontrado (usuário, role, permissão, sessão).

    Aceita um `resource_name` para compor uma mensagem específica sem
    precisar de uma subclasse dedicada para cada entidade do sistema.
    """

    error_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Recurso não encontrado."
    status_code = 404

    def __init__(self, resource_name: str = "Recurso", *, details: Any = None) -> None:
        super().__init__(f"{resource_name} não encontrado.", details=details)


class PermissionDeniedError(DomainException):
    """
    Levantada quando um usuário autenticado não possui a permissão
    exigida pela operação (RBAC).

    Distinta de `InvalidCredentialsError`/`token`: aqui a identidade do
    usuário já foi validada com sucesso — o problema é de autorização,
    não de autenticação.
    """

    error_code = ErrorCode.PERMISSION_DENIED
    default_message = "Você não tem permissão para executar esta ação."
    status_code = 403


class ValidationConflictError(DomainException):
    """
    Conflito de validação de negócio que não é um simples erro de
    formato de schema (ex: tentar excluir uma role em uso, atribuir uma
    permissão duplicada). Schemas Pydantic já cobrem erros de formato;
    esta exceção cobre invariantes de negócio verificadas pelo Service.
    """

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "A operação viola uma regra de negócio."
    status_code = 409


class RateLimitExceededError(DomainException):
    """Levantada pela camada de serviço/middleware quando um limite de taxa é excedido."""

    error_code = ErrorCode.RATE_LIMITED
    default_message = "Muitas requisições. Tente novamente mais tarde."
    status_code = 429
