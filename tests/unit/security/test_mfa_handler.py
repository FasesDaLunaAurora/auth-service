"""Testes unitários de `MFAHandler` — TOTP (RFC 6238), sem tocar banco/HTTP."""

from __future__ import annotations

import time

from app.security.mfa_handler import MFAHandler


def test_generate_secret_returns_base32_string_without_padding() -> None:
    secret = MFAHandler.generate_secret()
    assert secret == secret.upper() or secret.isalnum()
    assert "=" not in secret
    assert len(secret) >= 16


def test_generate_secret_is_random_each_time() -> None:
    assert MFAHandler.generate_secret() != MFAHandler.generate_secret()


def test_build_qr_code_uri_contains_expected_otpauth_fields() -> None:
    secret = MFAHandler.generate_secret()
    uri = MFAHandler.build_qr_code_uri(secret, account_email="user@example.com")

    assert uri.startswith("otpauth://totp/")
    assert f"secret={secret}" in uri
    assert "algorithm=SHA1" in uri
    assert "digits=6" in uri


def test_verify_code_accepts_the_currently_valid_code() -> None:
    secret = MFAHandler.generate_secret()
    current_code = MFAHandler.generate_current_code(secret)

    assert MFAHandler.verify_code(secret, current_code) is True


def test_verify_code_rejects_a_wrong_code() -> None:
    secret = MFAHandler.generate_secret()
    # Um código fixo com dígitos válidos, mas quase certamente incorreto
    # para o secret gerado aleatoriamente acima.
    assert MFAHandler.verify_code(secret, "000000") is False


def test_verify_code_rejects_malformed_input() -> None:
    secret = MFAHandler.generate_secret()
    assert MFAHandler.verify_code(secret, "abcdef") is False
    assert MFAHandler.verify_code(secret, "12345") is False  # 5 dígitos, não 6


def test_verify_code_tolerates_one_window_of_clock_skew() -> None:
    """
    Um código válido para a janela de tempo *anterior* ainda deve ser
    aceito (`valid_window=1` por padrão) — mitiga pequenas diferenças de
    relógio entre cliente e servidor, conforme prática comum de TOTP.
    """
    secret = MFAHandler.generate_secret()
    previous_window_time = time.time() - 30  # uma janela de 30s atrás
    previous_code = MFAHandler.generate_current_code(secret, for_time=previous_window_time)

    assert MFAHandler.verify_code(secret, previous_code, valid_window=1) is True
