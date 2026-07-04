"""
Script de seed: cria todas as permissões estruturais definidas em
`app.core.constants.PermissionCode` e uma role `admin` com todas elas
atribuídas.

Idempotente: pode ser executado quantas vezes forem necessárias — em
cada execução, apenas permissões/roles ainda inexistentes são criadas.

Uso:
    python scripts/seed_permissions.py

Este script usa a mesma configuração (`app.core.config.settings`) da
aplicação — nunca hardcodeie credenciais aqui. Ver `scripts/README.md`
para convenções de novos scripts.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Permite `python scripts/seed_permissions.py` a partir da raiz do
# projeto sem precisar instalar o pacote antes.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.constants import PermissionCode  # noqa: E402
from app.database.session import session_scope  # noqa: E402

# Importa TODOS os módulos de `app.models`, mesmo os não usados
# diretamente neste script. `Role` e `Permission` têm relacionamentos
# declarados por string (ex: `Mapped[list["User"]]`) — o SQLAlchemy só
# consegue resolver esses nomes se a classe referenciada já tiver sido
# importada em algum lugar do processo antes da primeira query. Sem
# isso, a configuração do mapper falha com
# `InvalidRequestError: ... failed to locate a name ('User')`. Mesmo
# import completo já usado em `alembic/env.py` e `tests/conftest.py`.
from app.models import (  # noqa: E402, F401
    permission_model,
    refresh_token_model,
    role_model,
    session_model,
    user_model,
)
from app.models.permission_model import Permission  # noqa: E402
from app.models.role_model import Role  # noqa: E402
from app.repositories.permission_repository import PermissionRepository  # noqa: E402
from app.repositories.role_repository import RoleRepository  # noqa: E402

_ADMIN_ROLE_NAME = "admin"
_ADMIN_ROLE_DESCRIPTION = "Acesso administrativo completo (criada pelo seed automático)."


def _all_permission_codes() -> list[str]:
    """Introspecta `PermissionCode` e retorna todos os códigos definidos como constantes."""
    return sorted(
        value
        for name, value in vars(PermissionCode).items()
        if not name.startswith("_") and isinstance(value, str)
    )


async def seed() -> None:
    codes = _all_permission_codes()
    created_permissions = 0
    all_permissions: list[Permission] = []

    async with session_scope() as session:
        permission_repo = PermissionRepository(session)
        role_repo = RoleRepository(session)

        for code in codes:
            existing = await permission_repo.get_by_code(code)
            if existing is not None:
                all_permissions.append(existing)
                continue

            permission = Permission(code=code, description=f"Permissão '{code}' (seed automático).")
            await permission_repo.create(permission)
            all_permissions.append(permission)
            created_permissions += 1

        admin_role = await role_repo.get_by_name(_ADMIN_ROLE_NAME)
        role_created = admin_role is None
        if admin_role is None:
            admin_role = Role(name=_ADMIN_ROLE_NAME, description=_ADMIN_ROLE_DESCRIPTION)
            await role_repo.create(admin_role)

        newly_assigned = 0
        for permission in all_permissions:
            was_new = await role_repo.assign_permission(admin_role, permission)
            if was_new:
                newly_assigned += 1

    print(f"Permissões existentes/definidas: {len(codes)}")
    print(f"Permissões criadas nesta execução: {created_permissions}")
    print(f"Role '{_ADMIN_ROLE_NAME}': {'criada' if role_created else 'já existia'}")
    print(f"Permissões atribuídas à role '{_ADMIN_ROLE_NAME}' nesta execução: {newly_assigned}")
    print(
        "\nPróximo passo: atribua a role 'admin' a um usuário via "
        "POST /api/v1/users/{user_id}/roles, ou marque is_superuser=True "
        "diretamente no banco para o primeiro usuário administrador."
    )


if __name__ == "__main__":
    asyncio.run(seed())
