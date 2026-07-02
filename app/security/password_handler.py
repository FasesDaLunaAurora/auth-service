"""
Handler de domínio para hashing/verificação de senha.

Camada fina sobre `app/core/security.py`, existindo para que
`app/services/*.py` importem de `app.security.password_handler`
(nomenclatura de domínio de segurança citada na Seção 3), sem conhecer
os detalhes de `passlib`/`CryptContext` diretamente.
"""

from __future__ import annotations

from app.core.security import hash_password, needs_rehash, verify_password


class PasswordHandler:
    """Fachada de hashing de senha usada pela camada de `services`."""

    @staticmethod
    def hash(plain_password: str) -> str:
        """Gera o hash de uma senha em texto puro."""
        return hash_password(plain_password)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """Verifica uma senha em texto puro contra um hash armazenado."""
        return verify_password(plain_password, hashed_password)

    @staticmethod
    def verify_and_rehash_if_needed(
        plain_password: str, hashed_password: str
    ) -> tuple[bool, str | None]:
        """
        Verifica a senha e, se válida e o hash estiver desatualizado
        (ex: scheme antigo, rounds diferentes), retorna um novo hash.

        Retorna `(is_valid, new_hash_or_none)`. A persistência do novo
        hash (se houver) é responsabilidade de `auth_service`/
        `user_service` — este handler nunca acessa o repositório.
        """
        is_valid = verify_password(plain_password, hashed_password)
        if not is_valid:
            return False, None
        if needs_rehash(hashed_password):
            return True, hash_password(plain_password)
        return True, None
