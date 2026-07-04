"""
Testes de API para `/api/v1/sessions` (Seção 6).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.repositories.user_repository import UserRepository

_PAYLOAD = {
    "email": "session-routes@example.com",
    "full_name": "Session Routes Test",
    "password": "ValidPass1",
    "password_confirm": "ValidPass1",
}


async def _register_verify_and_login(client: AsyncClient, db_session, *, email: str) -> dict:
    payload = {**_PAYLOAD, "email": email}
    await client.post("/api/v1/auth/register", json=payload)

    repo = UserRepository(db_session)
    user = await repo.get_by_email(email)
    user.is_verified = True
    await repo.update(user)

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": _PAYLOAD["password"]}
    )
    return login_response.json()


@pytest.mark.asyncio
async def test_list_sessions_shows_the_current_session(client: AsyncClient, db_session) -> None:
    tokens = await _register_verify_and_login(client, db_session, email="list-sessions@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.get("/api/v1/sessions", headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["is_current"] is True


@pytest.mark.asyncio
async def test_revoke_own_session_succeeds(client: AsyncClient, db_session) -> None:
    tokens = await _register_verify_and_login(
        client, db_session, email="revoke-own-session@example.com"
    )
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    list_response = await client.get("/api/v1/sessions", headers=headers)
    session_id = list_response.json()["items"][0]["id"]

    revoke_response = await client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert revoke_response.status_code == 204


@pytest.mark.asyncio
async def test_cannot_revoke_another_users_session(client: AsyncClient, db_session) -> None:
    """
    Checagem de posse do recurso (`SessionService.revoke_session`): um
    usuário não pode revogar a sessão de outro, mesmo sabendo o ID.
    """
    victim_tokens = await _register_verify_and_login(client, db_session, email="victim@example.com")
    attacker_tokens = await _register_verify_and_login(
        client, db_session, email="attacker@example.com"
    )

    victim_headers = {"Authorization": f"Bearer {victim_tokens['access_token']}"}
    victim_sessions = await client.get("/api/v1/sessions", headers=victim_headers)
    victim_session_id = victim_sessions.json()["items"][0]["id"]

    attacker_headers = {"Authorization": f"Bearer {attacker_tokens['access_token']}"}
    response = await client.delete(
        f"/api/v1/sessions/{victim_session_id}", headers=attacker_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_revoke_nonexistent_session_returns_404(client: AsyncClient, db_session) -> None:
    tokens = await _register_verify_and_login(client, db_session, email="revoke-404@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.delete(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
