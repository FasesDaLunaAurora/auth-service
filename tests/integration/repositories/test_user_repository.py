"""
Testes de integração de `UserRepository` — rodam contra o banco de
dados real de teste (fixture `db_session`, ver `tests/conftest.py`),
conforme a Seção 9.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.user_model import User
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_and_get_by_email(db_session) -> None:
    repo = UserRepository(db_session)
    user = User(email="Integration@Example.com", full_name="Integration Test", hashed_password="x")

    await repo.create(user)
    found = await repo.get_by_email("integration@example.com")

    assert found is not None
    assert found.id == user.id
    # O `@validates` do model normaliza o e-mail para minúsculas.
    assert found.email == "integration@example.com"


@pytest.mark.asyncio
async def test_soft_deleted_user_is_excluded_by_default(db_session) -> None:
    repo = UserRepository(db_session)
    user = User(email="deleted@example.com", full_name="Will Be Deleted", hashed_password="x")
    await repo.create(user)

    await repo.soft_delete(user, deleted_at=datetime.now(timezone.utc))

    assert await repo.get_by_id(user.id) is None
    assert await repo.get_by_id(user.id, include_deleted=True) is not None


@pytest.mark.asyncio
async def test_increment_failed_attempts_and_lock(db_session) -> None:
    repo = UserRepository(db_session)
    user = User(email="lockme@example.com", full_name="Lock Me", hashed_password="x")
    await repo.create(user)

    for _ in range(3):
        await repo.increment_failed_attempts(user)

    assert user.failed_login_attempts == 3

    await repo.reset_failed_attempts(user)
    assert user.failed_login_attempts == 0
