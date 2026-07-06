"""
Gerenciador de MFA via TOTP (RFC 6238).

Implementado do zero usando apenas a biblioteca padrão do Python (hmac,
hashlib, base64, etc.) para evitar dependências extras (como pyotp). O
algoritmo da RFC 6238 é simples e seguro o suficiente para essa abordagem direta.
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

_SECRET_BYTES_LENGTH = 20  # 160 bits — tamanho padrão recomendado para chaves TOTP

_CODE_DIGITS = 6


class MFAHandler:
    """Interface para geração e validação de códigos TOTP usada pelos services."""

    @staticmethod
    def generate_secret() -> str:
        """Gera uma nova chave TOTP em Base32 (padrão dos apps autenticadores)."""

        random_bytes = secrets.token_bytes(_SECRET_BYTES_LENGTH)
        return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")

    @staticmethod
    def build_qr_code_uri(secret: str, *, account_email: str) -> str:
        """
        Cria a URL `otpauth://totp/...` para ler no Google Authenticator ou Authy.
        """

        label = quote(f"{settings.MFA_ISSUER_NAME}:{account_email}")
        issuer = quote(settings.MFA_ISSUER_NAME)
        return (
            f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
            f"&algorithm=SHA1&digits={_CODE_DIGITS}&period={settings.MFA_CODE_VALID_SECONDS}"
        )

    @staticmethod
    def _generate_code_for_counter(secret: str, counter: int) -> str:
        """
        Implementa o HOTP (RFC 4226) com base no contador de tempo atual.

        Ajusta o padding em Base32 (múltiplo de 8), já que o segredo é
        guardado sem padding para o texto ficar mais limpo visualmente.
        """

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
        """Gera o código TOTP para o horário atual (usado apenas em testes)."""

        timestamp = for_time if for_time is not None else time.time()
        counter = int(timestamp // settings.MFA_CODE_VALID_SECONDS)
        return cls._generate_code_for_counter(secret, counter)

    @classmethod
    def verify_code(cls, secret: str, code: str, *, valid_window: int = 1) -> bool:
        """
        Valida o código TOTP enviado pelo usuário.

        O parâmetro `valid_window` aceita pequenas variações no relógio do
        dispositivo do usuário (para trás ou para frente). Isso evita falhas de
        autenticação por pequenos atrasos de sincronização com o servidor.
        """

        if not code.isdigit() or len(code) != _CODE_DIGITS:
            return False

        current_counter = int(time.time() // settings.MFA_CODE_VALID_SECONDS)
        for offset in range(-valid_window, valid_window + 1):
            expected_code = cls._generate_code_for_counter(secret, current_counter + offset)
            if hmac.compare_digest(expected_code, code):
                return True
        return False
