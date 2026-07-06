"""
Gerencia o hash e a verificação de senhas.

Funciona como uma camada simples sobre o `app/core/security.py`. Os services
usam este módulo diretamente, sem precisar conhecer detalhes do `passlib` ou
do `CryptContext`.
"""

from __future__ import annotations

from app.core.security import hash_password, needs_rehash, verify_password


class PasswordHandler:
    """Interface de hash de senha usada pelos services."""

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
        Valida a senha e gera um novo hash caso o atual esteja desatualizado.

        Retorna uma tupla `(is_valid, new_hash_or_none)`. Salvar o novo hash no
        banco é tarefa do `auth_service` ou `user_service`, pois este módulo não
        acessa o banco.
        """

        is_valid = verify_password(plain_password, hashed_password)
        if not is_valid:
            return False, None
        if needs_rehash(hashed_password):
            return True, hash_password(plain_password)
        return True, None
