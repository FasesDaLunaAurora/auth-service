"""
Testes de API (`httpx.AsyncClient`) para `/api/v1/auth`, cobrindo os
fluxos completos de autenticação e os casos de borda obrigatórios da
Seção 9: e-mail duplicado no cadastro, login com conta bloqueada.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.repositories.user_repository import UserRepository

_REGISTER_PAYLOAD = {
    "email": "api-test@example.com",
    "full_name": "API Test User",
    "password": "ValidPass1",
    "password_confirm": "ValidPass1",
}


async def _register_and_verify(client: AsyncClient, db_session, *, email: str) -> None:
    """Helper: registra um usuário e marca `is_verified=True` diretamente no banco.

    A confirmação de e-mail real depende de um token enviado por e-mail
    (não exposto na resposta HTTP, por design) — para testes de outros
    fluxos que exigem uma conta já confirmada, ajustamos o estado
    diretamente via repositório, mantendo o teste do fluxo de
    confirmação em si isolado e não bloqueando os demais.
    """
    payload = {**_REGISTER_PAYLOAD, "email": email}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    repo = UserRepository(db_session)
    user = await repo.get_by_email(email)
    user.is_verified = True
    await repo.update(user)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    """Caso de borda obrigatório (Seção 9): e-mail duplicado no cadastro."""
    first_response = await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert first_response.status_code == 201

    second_response = await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_fails_for_unverified_account(client: AsyncClient) -> None:
    payload = {**_REGISTER_PAYLOAD, "email": "unverified@example.com"}
    await client.post("/api/v1/auth/register", json=payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_login_success_returns_token_pair(client: AsyncClient, db_session) -> None:
    email = "verified-login@example.com"
    await _register_and_verify(client, db_session, email=email)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_invalid_credentials_returns_generic_message(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WhateverPass1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_account_locks_after_max_failed_login_attempts(
    client: AsyncClient, db_session
) -> None:
    """Caso de borda obrigatório (Seção 9): login com conta bloqueada."""
    email = "will-be-locked@example.com"
    await _register_and_verify(client, db_session, email=email)

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword1"},
        )
        assert response.status_code == 401

    locked_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )

    assert locked_response.status_code == 423
    assert locked_response.json()["error"]["code"] == "ACCOUNT_LOCKED"


async def test_access_protected_route_without_token_returns_401(client: AsyncClient) -> None:
    """
    `HTTPBearer` (usado em `auth_dependency.py`) retorna 401 quando o
    header `Authorization` está ausente — é o código correto (não
    autenticado); 403 seria para "autenticado, mas sem permissão".
    """
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_garbage_token_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-jwt"}
    )
    assert response.status_code == 401
