"""
Testes unitários de `AuthService`, com repositórios mockados (Seção 9:
"Unitários: cobrindo toda a camada services... com mocks dos
repositórios"). Cobre os casos de borda obrigatórios: login com conta
bloqueada, refresh token reutilizado após revogação, e-mail duplicado
no cadastro.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions.auth_exceptions import AccountLockedError, TokenRevokedError
from app.exceptions.user_exceptions import EmailAlreadyExistsError
from app.models.refresh_token_model import RefreshToken
from app.models.user_model import User
from app.schemas.auth_schema import LoginRequest, RefreshRequest, RegisterRequest
from app.security.password_handler import PasswordHandler
from app.services.auth_service import AuthService


def _build_service() -> tuple[AuthService, MagicMock, MagicMock, MagicMock, MagicMock]:
    user_repo = AsyncMock()
    refresh_token_repo = AsyncMock()
    session_repo = AsyncMock()
    email_client = AsyncMock()
    service = AuthService(
        user_repository=user_repo,
        refresh_token_repository=refresh_token_repo,
        session_repository=session_repo,
        email_client=email_client,
    )
    return service, user_repo, refresh_token_repo, session_repo, email_client


def _make_user(**overrides: object) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        hashed_password=PasswordHandler.hash("CorrectPass1"),
        is_active=True,
        is_verified=True,
        is_superuser=False,
        mfa_enabled=False,
        mfa_secret=None,
        locked_until=None,
        failed_login_attempts=0,
        roles=[],
    )
    defaults.update(overrides)
    user = User()
    for key, value in defaults.items():
        setattr(user, key, value)
    return user


@pytest.mark.asyncio
async def test_register_raises_when_email_already_exists() -> None:
    service, user_repo, *_ = _build_service()
    user_repo.exists_by_email.return_value = True

    payload = RegisterRequest(
        email="taken@example.com",
        full_name="Someone",
        password="ValidPass1",
        password_confirm="ValidPass1",
    )

    with pytest.raises(EmailAlreadyExistsError):
        await service.register(payload)

    user_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_login_with_locked_account_raises_account_locked_error() -> None:
    """Caso de borda obrigatório (Seção 9): login com conta bloqueada."""
    service, user_repo, *_ = _build_service()
    locked_user = _make_user(
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    user_repo.get_by_email.return_value = locked_user

    payload = LoginRequest(email=locked_user.email, password="CorrectPass1")

    with pytest.raises(AccountLockedError):
        await service.login(payload, ip_address="127.0.0.1", device_info="pytest")


@pytest.mark.asyncio
async def test_refresh_with_revoked_token_reuse_raises_and_revokes_everything() -> None:
    """
    Caso de borda obrigatório (Seção 9): refresh token reutilizado após
    revogação deve levantar `TokenRevokedError` e revogar todas as
    sessões/refresh tokens do usuário (proteção anti-replay, Seção 7).
    """
    service, user_repo, refresh_token_repo, session_repo, _ = _build_service()

    from app.security.jwt_handler import JWTHandler

    user = _make_user()
    issued_refresh = JWTHandler.create_refresh_token(user.id)

    stored_token = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=JWTHandler.hash_token(issued_refresh.token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked=True,  # já revogado — simula reuso/replay
    )
    refresh_token_repo.get_by_token_hash.return_value = stored_token

    payload = RefreshRequest(refresh_token=issued_refresh.token)

    with pytest.raises(TokenRevokedError):
        await service.refresh(payload)

    refresh_token_repo.revoke_all_for_user.assert_awaited_once_with(user.id)
    session_repo.revoke_all_for_user.assert_awaited_once_with(user.id)
