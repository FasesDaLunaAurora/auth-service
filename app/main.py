"""
Ponto de entrada do FastAPI.

Configura o logging, registra os tratadores de exceção, monta a pilha
de middlewares na ordem correta e inclui as rotas da API. Nenhuma regra
de negócio entra aqui.
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
    """Gerencia o ciclo de vida da aplicação"""
    logger.info("application_startup", app_name=settings.APP_NAME, env=settings.APP_ENV)
    yield
    logger.info("application_shutdown")
    await dispose_engine()
    await close_redis_client()


def create_app() -> FastAPI:
    """Cria a instância do FastAPI para facilitar testes e reaproveitamento do código."""

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

    # A ordem aqui importa porque os middlewares rodam de baixo para cima.
    # O CORS fica por fora de tudo para liberar os acessos logo de cara.
    # O Logging vem em seguida para medir o tempo total da resposta.
    # Já as travas de RateLimit e o Audit rodam por último, direto nas rotas.
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

    @app.get(f"{settings.API_VERSION_PREFIX}/health", tags=["Health"], summary="Health check")
    async def health_check() -> dict[str, str]:
        """
        Rota de health check para o Docker ou orquestradores (Kubernetes, ECS).

        Essa rota é uma necessidade padrão para monitorar a saúde da aplicação.
        Ela não exige login e não faz consultas ao banco ou Redis. Se o health check
        depender de serviços externos, uma instabilidade temporária no banco poderia
        derrubar o container sem real necessidade.
        """

        return {"status": "ok"}

    return app


app = create_app()
