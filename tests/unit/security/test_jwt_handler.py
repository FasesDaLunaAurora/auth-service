"""
Testes unitários de `JWTHandler` — cobre os casos de borda obrigatórios
da Seção 9 relacionados a token: expiração e tipo incompatível.
"""

from __future__ import annotations

import time
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from app.core.constants import TokenType
from app.exceptions.auth_exceptions import TokenExpiredError, TokenTypeMismatchError
from app.security.jwt_handler import JWTHandler


def test_create_and_decode_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    issued = JWTHandler.create_access_token(user_id)

    payload = JWTHandler.decode(issued.token, expected_type=TokenType.ACCESS)

    assert payload.sub == user_id
    assert payload.type == TokenType.ACCESS
    assert payload.jti == issued.jti


def test_access_token_embeds_session_id_claim() -> None:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    issued = JWTHandler.create_access_token(user_id, session_id=session_id)

    payload = JWTHandler.decode(issued.token, expected_type=TokenType.ACCESS)

    assert payload.sid == session_id


def test_decode_with_wrong_expected_type_raises_type_mismatch() -> None:
    user_id = uuid.uuid4()
    refresh = JWTHandler.create_refresh_token(user_id)

    with pytest.raises(TokenTypeMismatchError):
        JWTHandler.decode(refresh.token, expected_type=TokenType.ACCESS)


def test_expired_access_token_raises_token_expired_error() -> None:
    """Caso de borda obrigatório (Seção 9): expiração de access token."""
    user_id = uuid.uuid4()

    with patch(
        "app.security.jwt_handler.timedelta",
        return_value=timedelta(seconds=-1),
    ):
        issued = JWTHandler.create_access_token(user_id)

    time.sleep(0.01)
    with pytest.raises(TokenExpiredError):
        JWTHandler.decode(issued.token, expected_type=TokenType.ACCESS)


def test_hash_token_is_deterministic_and_never_the_raw_token() -> None:
    raw_token = "some.jwt.value"
    first_hash = JWTHandler.hash_token(raw_token)
    second_hash = JWTHandler.hash_token(raw_token)

    assert first_hash == second_hash
    assert first_hash != raw_token
