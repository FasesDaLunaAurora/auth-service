"""
Ponto de entrada da aplicação FastAPI.

Responsável por: configurar logging, registrar handlers de exceção,
montar a pilha de middlewares (na ordem correta) e incluir o router
agregado da API. Nenhuma regra de negócio vive aqui.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.database.session import dispose_engine
from app.exceptions.exception_handlers import register_exception_handlers
from app.integrations.redis_client import close_redis_client
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação (startup/shutdown)."""
    logger.info("application_startup", app_name=settings.APP_NAME, env=settings.APP_ENV)
    yield
    logger.info("application_shutdown")
    await dispose_engine()
    await close_redis_client()


def create_app() -> FastAPI:
    """Factory da aplicação FastAPI — facilita testes (`tests/conftest.py`) e reuso."""
    app = FastAPI(
        title="Auth Service",
        description=(
            "Microsserviço de autenticação e autorização — centraliza login, "
            "gestão de sessões, RBAC e MFA para sistemas clientes."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    # Ordem de montagem dos middlewares (Starlette executa o último
    # adicionado como o mais externo): Audit e RateLimit ficam mais
    # internos (só importam para rotas de negócio), Logging envolve tudo
    # para medir a duração total da requisição, e CORS fica no nível
    # mais externo, tratando preflight antes de qualquer outra lógica.
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"], summary="Health check")
    async def health_check() -> dict[str, str]:
        """
        Endpoint de health check, usado pelo `HEALTHCHECK` do Docker e por
        orquestradores (Kubernetes, ECS, etc).

        Não faz parte do contrato de endpoints da Seção 6 (que não define
        nenhuma rota de health check), mas é uma necessidade operacional
        padrão para qualquer serviço "pronto para produção" — por isso
        não exige autenticação nem acessa o banco/Redis (um health check
        que depende de infraestrutura externa pode causar reinícios em
        cascata caso o Postgres/Redis fiquem temporariamente
        indisponíveis).
        """
        return {"status": "ok"}

    return app


app = create_app()
