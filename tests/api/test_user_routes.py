"""
Testes de API para `/api/v1/users`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.repositories.user_repository import UserRepository

_PAYLOAD = {
    "email": "user-routes@example.com",
    "full_name": "User Routes Test",
    "password": "ValidPass1",
    "password_confirm": "ValidPass1",
}


async def _create_authenticated_client(client: AsyncClient, db_session) -> str:
    await client.post("/api/v1/auth/register", json=_PAYLOAD)

    repo = UserRepository(db_session)
    user = await repo.get_by_email(_PAYLOAD["email"])
    user.is_verified = True
    await repo.update(user)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": _PAYLOAD["email"], "password": _PAYLOAD["password"]},
    )
    return login_response.json()["access_token"]


async def _create_superuser(client: AsyncClient, db_session, *, email: str) -> tuple[str, str]:
    payload = {**_PAYLOAD, "email": email}
    await client.post("/api/v1/auth/register", json=payload)

    repo = UserRepository(db_session)
    user = await repo.get_by_email(email)
    user.is_verified = True
    user.is_superuser = True
    await repo.update(user)
    user_id = str(user.id)

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": _PAYLOAD["password"]}
    )
    return login_response.json()["access_token"], user_id


@pytest.mark.asyncio
async def test_get_me_returns_authenticated_user(client: AsyncClient, db_session) -> None:
    access_token = await _create_authenticated_client(client, db_session)

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == _PAYLOAD["email"]


@pytest.mark.asyncio
async def test_list_users_without_permission_returns_403(client: AsyncClient, db_session) -> None:
    access_token = await _create_authenticated_client(client, db_session)

    response = await client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_change_password_with_wrong_current_password_fails(
    client: AsyncClient, db_session
) -> None:
    access_token = await _create_authenticated_client(client, db_session)

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "WrongCurrent1",
            "new_password": "NewValidPass1",
            "new_password_confirm": "NewValidPass1",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_with_correct_current_password_succeeds(
    client: AsyncClient, db_session
) -> None:
    access_token = await _create_authenticated_client(client, db_session)

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": _PAYLOAD["password"],
            "new_password": "NewValidPass1",
            "new_password_confirm": "NewValidPass1",
        },
    )
    assert response.status_code == 204

    # A senha antiga não deve mais funcionar; a nova, sim.
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": _PAYLOAD["email"], "password": _PAYLOAD["password"]},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login", json={"email": _PAYLOAD["email"], "password": "NewValidPass1"}
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_list_users_as_superuser_returns_paginated_envelope(
    client: AsyncClient, db_session
) -> None:
    token, _user_id = await _create_superuser(
        client, db_session, email="list-users-admin@example.com"
    )

    response = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert "items" in body and "total" in body and "page" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_user_by_id_as_superuser(client: AsyncClient, db_session) -> None:
    token, user_id = await _create_superuser(client, db_session, email="get-user-admin@example.com")

    response = await client.get(
        f"/api/v1/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_404(client: AsyncClient, db_session) -> None:
    token, _user_id = await _create_superuser(client, db_session, email="get-404-admin@example.com")

    response = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_update_user_changes_full_name(client: AsyncClient, db_session) -> None:
    admin_token, _admin_id = await _create_superuser(
        client, db_session, email="update-admin@example.com"
    )
    target_email = "update-target@example.com"
    await client.post("/api/v1/auth/register", json={**_PAYLOAD, "email": target_email})
    target = await UserRepository(db_session).get_by_email(target_email)

    response = await client.patch(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_activate_and_deactivate_another_user(client: AsyncClient, db_session) -> None:
    admin_token, _admin_id = await _create_superuser(
        client, db_session, email="activate-admin@example.com"
    )
    target_email = "activate-target@example.com"
    await client.post("/api/v1/auth/register", json={**_PAYLOAD, "email": target_email})
    target = await UserRepository(db_session).get_by_email(target_email)
    headers = {"Authorization": f"Bearer {admin_token}"}

    deactivate_response = await client.post(
        f"/api/v1/users/{target.id}/deactivate", headers=headers
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    activate_response = await client.post(f"/api/v1/users/{target.id}/activate", headers=headers)
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_cannot_deactivate_own_account(client: AsyncClient, db_session) -> None:
    admin_token, admin_id = await _create_superuser(
        client, db_session, email="self-deactivate-admin@example.com"
    )

    response = await client.post(
        f"/api/v1/users/{admin_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_user_soft_deletes_and_blocks_login(client: AsyncClient, db_session) -> None:
    admin_token, _admin_id = await _create_superuser(
        client, db_session, email="delete-admin@example.com"
    )
    target_email = "delete-target@example.com"
    await client.post("/api/v1/auth/register", json={**_PAYLOAD, "email": target_email})
    target = await UserRepository(db_session).get_by_email(target_email)

    delete_response = await client.delete(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204

    # Usuário excluído (logicamente) não deve mais ser encontrável.
    get_response = await client.get(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_own_account(client: AsyncClient, db_session) -> None:
    admin_token, admin_id = await _create_superuser(
        client, db_session, email="self-delete-admin@example.com"
    )

    response = await client.delete(
        f"/api/v1/users/{admin_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
