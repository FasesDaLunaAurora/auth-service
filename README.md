# Auth Service

Microsserviço de **autenticação e autorização**, desacoplado de qualquer aplicação cliente, construído em **FastAPI** + **PostgreSQL** + **SQLAlchemy 2.x (async)**. Centraliza login, gestão de sessões, RBAC (roles/permissões) e MFA (TOTP), para que qualquer sistema cliente delegue essas responsabilidades via API em vez de reimplementá-las internamente.

## Stack

| Categoria | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Framework Web | FastAPI (async) |
| ORM | SQLAlchemy 2.x (`Mapped`/`mapped_column`, async) |
| Migrações | Alembic |
| Banco de dados | PostgreSQL 17 |
| Cache / Rate limiting | Redis |
| Hash de senha | passlib (bcrypt/argon2) |
| JWT | python-jose |
| Testes | Pytest + pytest-asyncio + httpx |
| Lint / Types | Ruff + Mypy (strict) |

## Arquitetura

Clean Architecture com regra de dependência estrita entre camadas:

```text
API (routes) → Services → Repositories → Database
```

- `api/` — controllers HTTP e injeção de dependências (FastAPI `Depends`).
- `services/` — toda regra de negócio; nunca importa `Request`/`HTTPException`.
- `repositories/` — apenas `SELECT`/`INSERT`/`UPDATE`/`DELETE`, sem regra de negócio.
- `models/` — entidades SQLAlchemy.
- `schemas/` — contratos Pydantic v2 de entrada/saída da API.
- `security/` — JWT, hashing de senha, MFA (TOTP), OAuth2.
- `middleware/` — rate limiting, logging estruturado, auditoria.
- `exceptions/` — exceções de domínio e sua tradução para HTTP.
- `integrations/` — Redis, SMTP, providers OAuth externos.

## Como rodar

### Com Docker (recomendado)

```bash
cp .env.example .env
# edite .env e defina um JWT_SECRET_KEY forte, ex: openssl rand -hex 32
docker compose up --build
```

A API sobe em `http://localhost:8000`. Documentação interativa (fora de produção) em `/docs` e `/redoc`.

### Localmente (sem Docker)

Requer PostgreSQL 17 e Redis rodando localmente.

```bash
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"
cp .env.example .env  # ajuste DATABASE_URL/REDIS_URL para localhost
alembic upgrade head
uvicorn app.main:app --reload
```

## Testes

```bash
pytest --cov=app --cov-report=term-missing
```

## Qualidade de código

```bash
ruff check .          # lint
ruff format --check . # formatação
mypy app              # checagem de tipos (strict)
```

## Principais endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/auth/register` | Cadastro de usuário |
| POST | `/api/v1/auth/login` | Login (retorna tokens ou desafio MFA) |
| POST | `/api/v1/auth/refresh` | Rotaciona o refresh token |
| POST | `/api/v1/auth/logout` | Revoga a sessão atual |
| GET | `/api/v1/users/me` | Usuário autenticado |
| GET | `/api/v1/sessions` | Sessões ativas do usuário |
| POST | `/api/v1/roles` | Cria uma role (RBAC) |

Contrato completo de endpoints, modelagem de dados e fluxos de segurança: ver a especificação técnica do projeto.

## Segurança

- Senhas com hash bcrypt/argon2, nunca em texto puro.
- JWT assinado (HS256 por padrão), secret via variável de ambiente.
- Refresh tokens armazenados apenas como hash SHA-256.
- Rotação de refresh token com proteção contra *replay* (reuso revoga todas as sessões).
- Bloqueio de conta após tentativas de login malsucedidas.
- Rate limiting por IP nas rotas de autenticação (Redis).
- Headers de segurança (`X-Frame-Options`, `HSTS`, etc.) em toda resposta.
- Logs de auditoria estruturados, nunca contendo senhas/tokens em texto puro.

## Changelog de decisões de implementação

Este projeto foi gerado a partir de uma especificação técnica detalhada. Onde a especificação era ambígua, incompleta ou internamente contraditória, as decisões tomadas foram documentadas diretamente nos arquivos afetados (comentários de "Nota de decisão") e resumidas a seguir:

1. **Sobreposição `core/security.py` vs. `security/`**: primitivas puras (passlib/jose/hashlib) ficaram em `core/security.py`; a camada de domínio de segurança (`JWTHandler`, `PasswordHandler`, `MFAHandler`, `OAuth2Handler`) ficou em `security/`, evitando duplicar configuração criptográfica.
2. **Campos de MFA ausentes na modelagem de dados**: a especificação define os endpoints `/auth/mfa/*`, mas não os campos correspondentes em `User` — adicionados `mfa_enabled`/`mfa_secret`.
3. **`session_schema.py` inexistente na árvore de pastas**: schemas de `Session` foram colocados em `auth_schema.py`.
4. **Repositórios/serviços/integrações "adiantados"**: `refresh_token_repository.py`, `session_repository.py`, `permission_service.py`, `session_service.py`, `email_client.py` e `redis_client.py` não estavam explicitamente no cronograma de etapas, mas são exigidos pela árvore de pastas e por dependências diretas de outros componentes — gerados assim que necessários.
5. **MFA (TOTP) implementado apenas com a *standard library*** (`hmac`, `base64`, `struct`), sem adicionar `pyotp`, respeitando a stack tecnológica travada pela Seção 2.
6. **Claim `sid` (session id) adicionada aos tokens**: necessária para que `POST /auth/logout` saiba qual `Session` revogar a partir do próprio access token, sem exigir esse dado no corpo da requisição.
7. **`Role`/`Permission` usam exclusão física**, diferente de `User` (exclusão lógica) — a especificação só define `deleted_at` para `User`.
8. **Regra de negócio adicional**: um usuário não pode desativar/excluir a própria conta via `/users/{id}` (`CannotDeactivateSelfError`) — não pedida explicitamente, alinhada às boas práticas de segurança da Seção 1.
9. **Paths de atribuição RBAC** (`/users/{id}/roles`, `/roles/{id}/permissions`) definidos por nós, já que a Seção 6 não fixa esse contrato.
10. **Endpoint de health check** (`GET /api/v1/health`) adicionado — necessidade operacional padrão não coberta pelo contrato de endpoints da especificação, usado pelo `HEALTHCHECK` do Docker.
11. **OAuth2 implementado como abstração genérica** (fluxo Authorization Code), já que a especificação menciona "OAuth2" na tabela de responsabilidades da camada de segurança, mas não define nenhum endpoint ou provider concreto.
