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
from app.security.jwt_handler import JWTHandler
from app.security.mfa_handler import MFAHandler

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


async def _register_verify_and_login(client: AsyncClient, db_session, *, email: str) -> dict:
    """Helper: registra, verifica e loga, retornando o corpo de `TokenResponse`."""
    await _register_and_verify(client, db_session, email=email)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    return response.json()


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


@pytest.mark.asyncio
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
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-jwt"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_successfully(client: AsyncClient, db_session) -> None:
    tokens = await _register_verify_and_login(client, db_session, email="refresh-ok@example.com")

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_with_already_used_token_revokes_all_sessions(
    client: AsyncClient, db_session
) -> None:
    """
    Caso de borda obrigatório (Seção 9): refresh token reutilizado após
    revogação. Usa o mesmo refresh token duas vezes — a segunda deve
    falhar, e uma terceira tentativa com o token *novo* (emitido na
    primeira rotação) também deve falhar, pois o replay revoga tudo.
    """
    tokens = await _register_verify_and_login(client, db_session, email="replay-attack@example.com")

    first_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first_refresh.status_code == 200
    rotated_tokens = first_refresh.json()

    # Reapresentar o token JÁ REVOGADO (reuso/replay).
    replay_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay_response.status_code == 401
    assert replay_response.json()["error"]["code"] == "TOKEN_REVOKED"

    # O token novo (da primeira rotação, legítimo) também deve ter sido
    # revogado como efeito colateral de segurança do replay detectado.
    second_refresh_attempt = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated_tokens["refresh_token"]}
    )
    assert second_refresh_attempt.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_the_refresh_token(client: AsyncClient, db_session) -> None:
    tokens = await _register_verify_and_login(client, db_session, email="logout@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_response.status_code == 204

    refresh_after_logout = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_revokes_every_session(client: AsyncClient, db_session) -> None:
    email = "logout-all@example.com"
    first_login = await _register_verify_and_login(client, db_session, email=email)

    second_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )
    second_login = second_login_response.json()

    headers = {"Authorization": f"Bearer {first_login['access_token']}"}
    logout_all_response = await client.post("/api/v1/auth/logout-all", headers=headers)
    assert logout_all_response.status_code == 204

    for tokens in (first_login, second_login):
        refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_always_returns_202(client: AsyncClient, db_session) -> None:
    """Nunca deve revelar se o e-mail existe ou não (Seção 8)."""
    existing_email = "forgot-password@example.com"
    await _register_and_verify(client, db_session, email=existing_email)

    for email in (existing_email, "does-not-exist@example.com"):
        response = await client.post("/api/v1/auth/password/forgot", json={"email": email})
        assert response.status_code == 202


@pytest.mark.asyncio
async def test_reset_password_with_valid_token_changes_password(
    client: AsyncClient, db_session
) -> None:
    email = "reset-password@example.com"
    await _register_and_verify(client, db_session, email=email)

    repo = UserRepository(db_session)
    user = await repo.get_by_email(email)
    reset_token = JWTHandler.create_password_reset_token(user.id)

    reset_response = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "token": reset_token.token,
            "new_password": "BrandNewPass1",
            "new_password_confirm": "BrandNewPass1",
        },
    )
    assert reset_response.status_code == 204

    old_password_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )
    assert old_password_login.status_code == 401

    new_password_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "BrandNewPass1"}
    )
    assert new_password_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_with_invalid_token_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "token": "not-a-real-jwt",
            "new_password": "BrandNewPass1",
            "new_password_confirm": "BrandNewPass1",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_email_with_valid_token_marks_user_verified(
    client: AsyncClient, db_session
) -> None:
    email = "confirm-email@example.com"
    register_response = await client.post(
        "/api/v1/auth/register", json={**_REGISTER_PAYLOAD, "email": email}
    )
    assert register_response.status_code == 201
    assert register_response.json()["is_verified"] is False

    repo = UserRepository(db_session)
    user = await repo.get_by_email(email)
    confirmation_token = JWTHandler.create_email_confirmation_token(user.id)

    confirm_response = await client.post(
        "/api/v1/auth/email/confirm", json={"token": confirmation_token.token}
    )
    assert confirm_response.status_code == 204

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_confirm_email_with_invalid_token_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/email/confirm", json={"token": "not-a-real-jwt"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_email_with_wrong_token_type_returns_401(
    client: AsyncClient, db_session
) -> None:
    """Um access token (tipo errado) não deve ser aceito como confirmação de e-mail."""
    tokens = await _register_verify_and_login(
        client, db_session, email="wrong-token-type@example.com"
    )
    response = await client.post(
        "/api/v1/auth/email/confirm", json={"token": tokens["access_token"]}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_enable_mfa_then_login_requires_mfa_challenge(
    client: AsyncClient, db_session
) -> None:
    email = "mfa-enable@example.com"
    tokens = await _register_verify_and_login(client, db_session, email=email)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    enable_response = await client.post("/api/v1/auth/mfa/enable", headers=headers)
    assert enable_response.status_code == 200
    secret = enable_response.json()["secret"]
    assert enable_response.json()["qr_code_uri"].startswith("otpauth://totp/")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["mfa_required"] is True
    assert "challenge_token" in body

    valid_code = MFAHandler.generate_current_code(secret)
    verify_response = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": body["challenge_token"], "code": valid_code},
    )
    assert verify_response.status_code == 200
    assert "access_token" in verify_response.json()


@pytest.mark.asyncio
async def test_verify_mfa_with_invalid_code_returns_401(client: AsyncClient, db_session) -> None:
    email = "mfa-invalid-code@example.com"
    tokens = await _register_verify_and_login(client, db_session, email=email)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    await client.post("/api/v1/auth/mfa/enable", headers=headers)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _REGISTER_PAYLOAD["password"]},
    )
    challenge_token = login_response.json()["challenge_token"]

    verify_response = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": challenge_token, "code": "000000"},
    )
    assert verify_response.status_code == 401
    assert verify_response.json()["error"]["code"] == "MFA_INVALID_CODE"
