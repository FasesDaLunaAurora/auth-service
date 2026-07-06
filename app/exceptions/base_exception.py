"""
Exceção base e erros genéricos compartilhados entre os módulos.

Regra de arquitetura: os services lançam apenas estas exceções (ou suas
subclasses), nunca `HTTPException`. A conversão para HTTP ocorre apenas no
`exception_handlers.py`, que usa o `status_code` mapeado na própria classe
para não criar dependências do FastAPI na camada de negócio.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import ErrorCode


class DomainException(Exception):
    """
    Classe base para as exceções de negócio da aplicação.

    As subclasses devem definir `error_code`, `default_message` e `status_code`.
    O campo `details` é opcional e serve para dar contexto extra (não logue
    dados sensíveis como senhas ou tokens aqui).
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
    Erro de recurso não encontrado.
    Aceita o `resource_name` para gerar a mensagem específica,
    evitando a criação de uma subclasse para cada tabela/entidade.
    """

    error_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Recurso não encontrado."
    status_code = 404

    def __init__(self, resource_name: str = "Recurso", *, details: Any = None) -> None:
        super().__init__(f"{resource_name} não encontrado.", details=details)


class PermissionDeniedError(DomainException):
    """
    Erro de permissão insuficiente (RBAC).

    Aqui a identidade do usuário já foi validada com sucesso, mas ele
    não tem autorização para executar a operação (erro 403, não 401).
    """

    error_code = ErrorCode.PERMISSION_DENIED
    default_message = "Você não tem permissão para executar esta ação."
    status_code = 403


class ValidationConflictError(DomainException):
    """
    Erro de conflito ou regra de negócio violada.

    Usada para cenários que o Pydantic não cobre sozinhos (ex: excluir role em uso
    ou duplicar permissão). Valida as regras que dependem de consulta ao banco.
    """

    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "A operação viola uma regra de negócio."
    status_code = 409


class RateLimitExceededError(DomainException):
    """Lançada quando o limite de requisições (rate limit) é excedido."""

    error_code = ErrorCode.RATE_LIMITED
    default_message = "Muitas requisições. Tente novamente mais tarde."
    status_code = 429
