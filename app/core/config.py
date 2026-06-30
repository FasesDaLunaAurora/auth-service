"""
Configuração centralizada da aplicação.

Todas as variáveis de ambiente obrigatórias são validadas na inicialização
(Fail Fast). Se qualquer variável obrigatória estiver ausente ou inválida,
a aplicação deve falhar imediatamente ao subir, e não em tempo de execução.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações da aplicação, carregadas de variáveis de ambiente / .env.

    Decisão de implementação: usamos `pydantic_settings.BaseSettings` (Pydantic v2)
    em vez de ler `os.environ` manualmente, pois isso nos dá validação de tipos,
    valores default explícitos e falha rápida automática quando um campo
    obrigatório (sem default) não é fornecido — alinhado à Seção 8 da especificação.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )

    # --- Aplicação ---
    APP_NAME: str = "auth-service"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Servidor ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Banco de dados (obrigatório, sem default => Fail Fast se ausente) ---
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="URL assíncrona do PostgreSQL, ex: postgresql+asyncpg://user:pass@host:5432/db",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # --- Redis (obrigatório: usado por rate limiting e blacklist de tokens) ---
    REDIS_URL: RedisDsn = Field(..., description="URL de conexão do Redis")

    # --- JWT / Segurança (obrigatório, nunca hardcoded) ---
    JWT_SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret usado para assinar tokens JWT (HMAC). Mínimo 32 caracteres.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Política de senha e bloqueio por força bruta ---
    PASSWORD_MIN_LENGTH: int = 8
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # --- Rate limiting global (por IP, nas rotas de autenticação) ---
    RATE_LIMIT_AUTH_REQUESTS: int = 10
    RATE_LIMIT_AUTH_WINDOW_SECONDS: int = 60

    # --- MFA ---
    MFA_ISSUER_NAME: str = "AuthService"

    # --- E-mail / SMTP (usado em confirmação de e-mail e reset de senha) ---
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: bool = True

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: list[AnyUrl] | list[Literal["*"]] = ["*"]

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_JSON: bool = True

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _validate_jwt_secret_strength(cls, value: str) -> str:
        """
        Validação defensiva adicional: rejeita secrets triviais mesmo que
        cumpram o tamanho mínimo (ex: 32 caracteres repetidos).
        Decisão de implementação não explicitada na especificação original.
        """
        if len(set(value)) < 8:
            raise ValueError(
                "JWT_SECRET_KEY tem baixa entropia (poucos caracteres distintos). "
                "Utilize um valor gerado aleatoriamente, ex: `openssl rand -hex 32`."
            )
        return value

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna a instância única (cacheada) de Settings.

    Uso de `lru_cache` em vez de uma variável global simples para permitir
    substituição controlada em testes via `get_settings.cache_clear()`
    combinado com monkeypatch de variáveis de ambiente.
    """
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
