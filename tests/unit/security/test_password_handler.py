"""Testes unitários de `PasswordHandler` — não tocam banco de dados nem HTTP."""

from __future__ import annotations

from app.security.password_handler import PasswordHandler


def test_hash_is_never_the_plain_password() -> None:
    hashed = PasswordHandler.hash("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"
    assert hashed.startswith("$2b$") or hashed.startswith("$argon2")


def test_verify_correct_password_returns_true() -> None:
    hashed = PasswordHandler.hash("Sup3rSecret!")
    assert PasswordHandler.verify("Sup3rSecret!", hashed) is True


def test_verify_incorrect_password_returns_false() -> None:
    hashed = PasswordHandler.hash("Sup3rSecret!")
    assert PasswordHandler.verify("WrongPassword1", hashed) is False


def test_verify_malformed_hash_returns_false_not_raises() -> None:
    assert PasswordHandler.verify("anything", "not-a-real-hash") is False


def test_verify_and_rehash_if_needed_returns_none_when_scheme_is_current() -> None:
    hashed = PasswordHandler.hash("Sup3rSecret!")
    is_valid, new_hash = PasswordHandler.verify_and_rehash_if_needed("Sup3rSecret!", hashed)
    assert is_valid is True
    assert new_hash is None


def test_verify_and_rehash_if_needed_returns_false_on_wrong_password() -> None:
    hashed = PasswordHandler.hash("Sup3rSecret!")
    is_valid, new_hash = PasswordHandler.verify_and_rehash_if_needed("wrong", hashed)
    assert is_valid is False
    assert new_hash is None
