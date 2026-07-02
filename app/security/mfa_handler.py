"""
Handler de domínio para MFA via TOTP (RFC 6238).

Nota de decisão: a Seção 2 (Stack Tecnológica) não lista nenhuma
biblioteca de TOTP (ex: `pyotp`), e a regra "não substitua nenhuma
tecnologia desta lista" trata de substituições, não de adições — ainda
assim, optei por implementar TOTP usando apenas a *standard library*
(`hmac`, `hashlib`, `base64`, `struct`, `secrets`), evitando introduzir
qualquer dependência nova não prevista na especificação. RFC 6238 é um
algoritmo simples o suficiente para isso ser seguro e direto.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from app.core.config import settings

_SECRET_BYTES_LENGTH = 20  # 160 bits — recomendação padrão para chaves TOTP
_CODE_DIGITS = 6


class MFAHandler:
    """Fachada de geração/verificação de código TOTP usada pela camada de `services`."""

    @staticmethod
    def generate_secret() -> str:
        """Gera um novo secret TOTP, codificado em Base32 (formato exigido pelos apps autenticadores)."""
        random_bytes = secrets.token_bytes(_SECRET_BYTES_LENGTH)
        return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")

    @staticmethod
    def build_qr_code_uri(secret: str, *, account_email: str) -> str:
        """
        Monta a URI `otpauth://totp/...` para leitura por um app
        autenticador (Google Authenticator, Authy, etc).
        """
        label = quote(f"{settings.MFA_ISSUER_NAME}:{account_email}")
        issuer = quote(settings.MFA_ISSUER_NAME)
        return (
            f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
            f"&algorithm=SHA1&digits={_CODE_DIGITS}&period={settings.MFA_CODE_VALID_SECONDS}"
        )

    @staticmethod
    def _generate_code_for_counter(secret: str, counter: int) -> str:
        """Implementa HOTP (RFC 4226), base do TOTP, para um contador de tempo específico."""
        # Base32 exige padding múltiplo de 8 — reconstituído aqui pois o
        # secret é armazenado/exibido sem padding por conveniência visual.
        padded_secret = secret + "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(padded_secret.upper())
        counter_bytes = struct.pack(">Q", counter)

        digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        truncated = digest[offset : offset + 4]
        code_int = (struct.unpack(">I", truncated)[0] & 0x7FFFFFFF) % (10**_CODE_DIGITS)
        return str(code_int).zfill(_CODE_DIGITS)

    @classmethod
    def generate_current_code(cls, secret: str, *, for_time: float | None = None) -> str:
        """Gera o código TOTP válido para o instante atual (usado apenas em testes)."""
        timestamp = for_time if for_time is not None else time.time()
        counter = int(timestamp // settings.MFA_CODE_VALID_SECONDS)
        return cls._generate_code_for_counter(secret, counter)

    @classmethod
    def verify_code(cls, secret: str, code: str, *, valid_window: int = 1) -> bool:
        """
        Verifica um código TOTP informado pelo usuário.

        `valid_window` tolera desvios de relógio entre cliente e
        servidor (janelas para trás/frente), conforme prática comum de
        implementações TOTP — sem isso, pequenas diferenças de horário
        no dispositivo do usuário causariam falhas de MFA legítimas.
        """
        if not code.isdigit() or len(code) != _CODE_DIGITS:
            return False

        current_counter = int(time.time() // settings.MFA_CODE_VALID_SECONDS)
        for offset in range(-valid_window, valid_window + 1):
            expected_code = cls._generate_code_for_counter(secret, current_counter + offset)
            if hmac.compare_digest(expected_code, code):
                return True
        return False
