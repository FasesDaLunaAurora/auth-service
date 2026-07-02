"""
Testes de API para `/api/v1/users`, incluindo o caso de borda
obrigatório (Seção 9): acesso a rota protegida sem permissão.
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
    """Registra, verifica e loga um usuário comum (sem roles), retornando o access token."""
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


@pytest.mark.asyncio
async def test_get_me_returns_authenticated_user(client: AsyncClient, db_session) -> None:
    access_token = await _create_authenticated_client(client, db_session)

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == _PAYLOAD["email"]


@pytest.mark.asyncio
async def test_list_users_without_permission_returns_403(
    client: AsyncClient, db_session
) -> None:
    """Caso de borda obrigatório (Seção 9): acesso a rota protegida sem permissão."""
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
