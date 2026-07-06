"""
Testes de API para `/api/v1/permissions` (CRUD completo).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.repositories.user_repository import UserRepository

_PAYLOAD = {
    "email": "admin-permission-routes@example.com",
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
async def test_create_list_update_and_delete_permission(client: AsyncClient, db_session) -> None:
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/permissions",
        headers=headers,
        json={"code": "report:export", "description": "Exportar relatórios"},
    )
    assert create_response.status_code == 201
    permission_id = create_response.json()["id"]
    assert create_response.json()["code"] == "report:export"

    list_response = await client.get("/api/v1/permissions", headers=headers)
    assert list_response.status_code == 200
    assert any(p["id"] == permission_id for p in list_response.json())

    update_response = await client.patch(
        f"/api/v1/permissions/{permission_id}",
        headers=headers,
        json={"description": "Exportar relatórios financeiros"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Exportar relatórios financeiros"

    delete_response = await client.delete(f"/api/v1/permissions/{permission_id}", headers=headers)
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_create_permission_with_invalid_code_format_returns_422(
    client: AsyncClient, db_session
) -> None:
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/permissions",
        headers=headers,
        json={"code": "Not A Valid Code!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_permission_with_duplicate_code_returns_conflict(
    client: AsyncClient, db_session
) -> None:
    token = await _create_superuser_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/permissions", headers=headers, json={"code": "widget:duplicate"})
    second_response = await client.post(
        "/api/v1/permissions", headers=headers, json={"code": "widget:duplicate"}
    )
    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_permission_routes_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/permissions")
    assert response.status_code == 401
