"""
Dependência de autorização RBAC: gera uma dependência do FastAPI que
exige uma permissão específica do usuário autenticado.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from app.api.dependencies.auth_dependency import CurrentUser
from app.exceptions.base_exception import PermissionDeniedError
from app.models.user_model import User
from app.services.role_service import RoleService


def require_permission(permission_code: str) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Fábrica de dependências de autorização.

    Uso em uma rota:
    ```python
    @router.get("/users", dependencies=[Depends(require_permission(PermissionCode.USER_LIST))])
    ```

    A checagem de RBAC em si (`RoleService.user_has_permission`) é um
    método estático puro sobre os relacionamentos já carregados do
    `User` (via `lazy="selectin"` nos models, Etapa 2) — não é
    necessária uma nova consulta ao banco só para autorizar.
    """

    async def _dependency(current_user: CurrentUser) -> User:
        if not RoleService.user_has_permission(current_user, permission_code):
            raise PermissionDeniedError(
                f"Esta operação exige a permissão '{permission_code}'."
            )
        return current_user

    return _dependency
