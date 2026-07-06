"""Filtro RBAC: gera uma dependência do FastAPI para validar permissões específicas."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from app.api.dependencies.auth_dependency import CurrentUser
from app.exceptions.base_exception import PermissionDeniedError
from app.models.user_model import User
from app.services.role_service import RoleService


def require_permission(permission_code: str) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Fábrica de dependências para controle de acesso (RBAC).

    Exemplo de uso:
    ```python
    @router.get("/users", dependencies=[Depends(require_permission(PermissionCode.USER_LIST))])
    ```

    A checagem (`RoleService.user_has_permission`) roda em memória usando as
    relações já carregadas no usuário (via selectinload). Nenhuma query extra
    é disparada no banco para validar a permissão.
    """

    async def _dependency(current_user: CurrentUser) -> User:
        if not RoleService.user_has_permission(current_user, permission_code):
            raise PermissionDeniedError(f"Esta operação exige a permissão '{permission_code}'.")
        return current_user

    return _dependency
