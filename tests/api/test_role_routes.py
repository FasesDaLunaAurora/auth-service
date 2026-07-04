"""
Testes de API para `/api/v1/roles`. Usa um usuário `is_superuser=True`
(bypass de RBAC, ver `RoleService.user_has_permission`) para exercitar o
CRUD sem depender de um fluxo de seed de permissões.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.repositories.user_repository import UserRepository

_PAYLOAD = {
    "email": "admin-role-routes@example.com",
    "full_name": "Admin",
    "password": "ValidPass1",
    "password_confirm": "ValidPass1",
}


async def _create_superuser_token(client: AsyncClient, db_session) -> str:
    await client.post("/api/v1/auth/register", json=_PAYLOAD)

    repo = UserRepository(db_session)
    user = await repo.get_by_email(_PAYLOAD["email"])
    user.is_verified = True
    user.is_superuser = True
    await repo.update(user)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": _PAYLOAD["email"], "password": _PAYLOAD["password"]},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_list_and_delete_role(client: AsyncClient, db_session) -> None:
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/roles",
        headers=headers,
        json={"name": "editor", "description": "Pode editar conteúdo"},
    )
    assert create_response.status_code == 201
    role_id = create_response.json()["id"]

    list_response = await client.get("/api/v1/roles", headers=headers)
    assert list_response.status_code == 200
    assert any(role["id"] == role_id for role in list_response.json())

    delete_response = await client.delete(f"/api/v1/roles/{role_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_role_with_duplicate_name_returns_conflict(
    client: AsyncClient, db_session
) -> None:
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/roles", headers=headers, json={"name": "duplicate-role"})
    second_response = await client.post(
        "/api/v1/roles", headers=headers, json={"name": "duplicate-role"}
    )

    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_assign_and_revoke_permission_on_a_freshly_created_role(
    client: AsyncClient, db_session
) -> None:
    """
    Cobre o caminho exato que quebrava com `MissingGreenlet`
    (`RoleRepository.assign_permission` acessando `role.permissions`
    logo após criar a role, sem um refresh explícito) — esta rota nunca
    tinha sido exercitada por teste algum antes desse bug aparecer em
    uso manual.
    """
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    role_response = await client.post(
        "/api/v1/roles", headers=headers, json={"name": "role-with-perms"}
    )
    assert role_response.status_code == 201
    role_id = role_response.json()["id"]

    permission_response = await client.post(
        "/api/v1/permissions",
        headers=headers,
        json={"code": "widget:manage", "description": "Gerenciar widgets"},
    )
    assert permission_response.status_code == 201
    permission_id = permission_response.json()["id"]

    assign_response = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        headers=headers,
        json={"permission_id": permission_id},
    )
    assert assign_response.status_code == 200
    assert any(p["id"] == permission_id for p in assign_response.json()["permissions"])

    # Atribuir de novo (idempotência) não deve duplicar nem quebrar.
    repeat_response = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        headers=headers,
        json={"permission_id": permission_id},
    )
    assert repeat_response.status_code == 200
    assert len(repeat_response.json()["permissions"]) == 1

    revoke_response = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{permission_id}", headers=headers
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["permissions"] == []


@pytest.mark.asyncio
async def test_assign_and_revoke_role_on_a_user(client: AsyncClient, db_session) -> None:
    """Cobre `UserRepository.assign_role`/`remove_role` — mesmo padrão de risco corrigido."""
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    role_response = await client.post(
        "/api/v1/roles", headers=headers, json={"name": "role-for-user"}
    )
    role_id = role_response.json()["id"]

    repo = UserRepository(db_session)
    target_user = await repo.get_by_email(_PAYLOAD["email"])

    assign_response = await client.post(
        f"/api/v1/users/{target_user.id}/roles",
        headers=headers,
        json={"role_id": role_id},
    )
    assert assign_response.status_code == 200

    revoke_response = await client.delete(
        f"/api/v1/users/{target_user.id}/roles/{role_id}", headers=headers
    )
    assert revoke_response.status_code == 204
