"""
Configuração da aplicação via variáveis de ambiente.

Todas as configurações sensíveis ou dependentes de ambiente vivem aqui,
carregadas via `pydantic-settings`. Nenhuma outra camada deve ler
`os.environ` diretamente — isso garante um único ponto de verdade e
permite "Fail Fast": se uma variável obrigatória estiver ausente ou
inválida, a aplicação falha na inicialização, antes de aceitar qualquer
requisição.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações centrais do Auth Service.

    Instanciar esta classe sem as variáveis obrigatórias definidas no
    ambiente (ou em um arquivo `.env`) levanta `pydantic.ValidationError`
    imediatamente — este é o mecanismo de Fail Fast exigido pela
    especificação de segurança do projeto.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicação ---
    APP_NAME: str = "auth-service"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # --- Banco de dados ---
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="URL assíncrona do PostgreSQL, ex: postgresql+asyncpg://user:pass@host:5432/db",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT_SECONDS: int = 30
    DATABASE_ECHO: bool = False

    # --- Redis (cache / rate limiting) ---
    REDIS_URL: RedisDsn = Field(..., description="URL do Redis, ex: redis://host:6379/0")

    # --- JWT / Segurança ---
    JWT_SECRET_KEY: SecretStr = Field(
        ..., min_length=32, description="Secret HMAC para assinatura de tokens JWT."
    )
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512", "RS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ISSUER: str = "auth-service"

    # --- Hash de senha ---
    PASSWORD_HASH_SCHEME: Literal["bcrypt", "argon2"] = "bcrypt"
    BCRYPT_ROUNDS: int = 12

    # --- Política de conta / brute force ---
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # --- Rate limiting global (por IP) ---
    RATE_LIMIT_AUTH_REQUESTS: int = 10
    RATE_LIMIT_AUTH_WINDOW_SECONDS: int = 60

    # --- MFA ---
    MFA_ISSUER_NAME: str = "AuthService"
    MFA_CODE_VALID_SECONDS: int = 30

    # --- E-mail / SMTP (integrations/email_client.py) ---
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_FROM_EMAIL: str = "no-reply@auth-service.local"
    SMTP_USE_TLS: bool = True

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_JSON: bool = True

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _validate_secret_strength(cls, value: SecretStr) -> SecretStr:
        """Garante que o secret de JWT não seja um placeholder trivial."""
        weak_values = {"changeme", "secret", "123456", ""}
        if value.get_secret_value().lower() in weak_values:
            raise ValueError(
                "JWT_SECRET_KEY não pode ser um valor trivial/placeholder. "
                "Gere um secret forte, ex: `openssl rand -hex 32`."
            )
        return value

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna a instância de `Settings`, cacheada em memória.

    Usar `lru_cache` transforma esta função em um singleton simples e
    compatível com o sistema de Dependency Injection do FastAPI
    (`Depends(get_settings)`), sem custo de re-parsing a cada chamada.
    """
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
