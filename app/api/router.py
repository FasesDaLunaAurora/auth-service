"""
Agregador de todas as rotas da API sob o prefixo versionado
(`API_V1_PREFIX`, Seção 6).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    auth_routes,
    permission_routes,
    role_routes,
    session_routes,
    user_routes,
)
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)

api_router.include_router(auth_routes.router)
api_router.include_router(user_routes.router)
api_router.include_router(role_routes.router)
api_router.include_router(permission_routes.router)
api_router.include_router(session_routes.router)
