"""
Script de seed: cria as permissões padrão do sistema e o perfil `admin` com acesso total.

É idempotente, ou seja, pode ser rodado várias vezes sem duplicar dados. Ele só vai
criar o que ainda não existir no banco.

Uso:
    python scripts/seed_permissions.py

O script usa as configurações oficiais do sistema, sem nenhuma senha ou credencial
fixa no código (hardcoded).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Permite rodar o script direto da raiz sem precisar instalar o projeto como pacote.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.constants import PermissionCode  # noqa: E402
from app.database.session import session_scope  # noqa: E402

# Importa todos os modelos para que o SQLAlchemy consiga resolver os relacionamentos.
# Como o mapeamento usa strings (ex: 'User'), o framework precisa que as classes
# referenciadas estejam carregadas na memória para evitar erros de mapeamento inválido.
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
    """Varre o `PermissionCode` e retorna todos os códigos definidos nele."""

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
