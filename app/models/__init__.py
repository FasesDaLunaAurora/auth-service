"""
Pacote `app/models`.

A importação de todos os modelos aqui garante que `Base.metadata` (usado
pelo Alembic em `alembic/env.py`) conheça *todas* as tabelas, independente
da ordem de importação dos módulos individuais em outros pontos da aplicação.

Este arquivo também resolve a cadeia de importações circulares entre os
modelos: ao importar por este pacote, todos os modelos são carregados de
uma vez, antes que qualquer `relationship` tente resolver strings de forward
references.
"""

from app.models.permission_model import Permission
from app.models.refresh_token_model import RefreshToken
from app.models.role_model import Role, role_permissions
from app.models.session_model import Session
from app.models.user_model import User, user_roles

__all__ = [
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    "Session",
    "user_roles",
    "role_permissions",
]
