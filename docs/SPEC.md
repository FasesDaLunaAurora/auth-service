# Especificação Técnica — Auth Service

Este documento reúne o levantamento de requisitos e as decisões técnicas definidas antes (e ajustadas ao longo) do desenvolvimento deste projeto. Serve como referência de arquitetura e como registro do que foi decidido e por quê — útil tanto para retomar o projeto depois de um tempo parado quanto para quem for contribuir.

---

## 1. Contexto e Objetivo do Projeto

O **Auth Service** é um microsserviço de autenticação e autorização, desacoplado de qualquer aplicação cliente, construído em **Python com FastAPI**, **PostgreSQL** como banco de dados e **SQLAlchemy 2.x** como ORM, com migrações via **Alembic**.

O objetivo é centralizar **autenticação**, **autorização** e **gestão de usuários**, de modo que qualquer sistema cliente possa delegar essas responsabilidades a este serviço via API, sem precisar reimplementar login, controle de sessão ou RBAC internamente a cada novo projeto.

O projeto foi pensado desde o início como **pronto para produção e reutilizável como base para outros projetos** — não como protótipo ou MVP descartável. Isso implica: sem placeholders de "implementar depois", com tratamento de erro completo e testes cobrindo os fluxos críticos antes de considerar qualquer etapa "concluída".

### Princípios de engenharia adotados

- **Clean Architecture** com separação estrita de camadas (ver Seção 3)
- **SOLID**
- **Dependency Injection** (via sistema de dependências do FastAPI)
- **Repository Pattern** — acesso a dados isolado em repositórios
- **Service Layer** — toda regra de negócio centralizada em services
- **Programação defensiva** e **Fail Fast / Fail Secure**
- **Security by Design** — segurança tratada como parte de cada decisão, não como camada adicionada depois
- Recomendações **OWASP** para APIs (OWASP API Security Top 10)
- Tipagem forte em todo o código (type hints completos, validados com Mypy em modo strict)
- Código testável: nenhuma camada deve impedir testes unitários isolados das demais

### Regra de dependência entre camadas

```text
API → Services → Repositories → Database
```

- Camadas inferiores **nunca** importam ou conhecem camadas superiores.
- `Repositories` nunca conhecem `Services`.
- `Services` nunca conhecem detalhes de HTTP (nunca importam `Request`, `Response`, `HTTPException` diretamente — exceções de domínio são traduzidas para HTTP apenas na camada de API).
- `Schemas` (Pydantic) nunca são usados como entidades de banco; `Models` (SQLAlchemy) nunca são expostos diretamente na API.

---

## 2. Stack Tecnológica

| Categoria | Tecnologia | Versão mínima |
|---|---|---|
| Linguagem | Python | 3.11+ |
| Framework Web | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.x (estilo `Mapped`/`mapped_column`, async) |
| Migrações | Alembic | mais recente compatível |
| Banco de dados | PostgreSQL | 17 |
| Driver de banco | asyncpg | — |
| Validação | Pydantic | v2 |
| Hash de senha | passlib com bcrypt (ou argon2-cffi) | — |
| JWT | python-jose | — |
| Testes | Pytest + pytest-asyncio + httpx (AsyncClient) | — |
| Lint/Format | Ruff | — |
| Type checking | Mypy (modo strict) | — |
| Containerização | Docker (ou Podman) + Compose | — |
| CI | GitHub Actions | — |
| Cache/Rate limiting | Redis | — |

A stack foi fixada no início do projeto e mantida sem substituições ao longo do desenvolvimento (ex: sem trocar SQLAlchemy por outro ORM, sem trocar PostgreSQL por um banco não-relacional) — decisão tomada para manter previsibilidade e evitar retrabalho de infraestrutura no meio do caminho.

---

## 3. Arquitetura em Camadas

```text
                           Cliente
                               │
                      Requisição HTTP
                               │
                               ▼
                     ┌──────────────────┐
                     │     FastAPI      │
                     │   (Controllers)  │
                     └────────┬─────────┘
                              │
                              ▼
                    Camada de Dependências
          (Autenticação, Autorização, Validação)
                              │
                              ▼
                     Camada de Serviços
                  (Regras de Negócio)
                              │
                              ▼
                  Camada de Repositórios
                              │
                              ▼
                     PostgreSQL Database
```

### Responsabilidade de cada camada

| Camada | Responsabilidade | Proibições |
|---|---|---|
| `api/routes` | Receber requisição HTTP, validar input via Schema, chamar Service, traduzir resultado/exceção para Response | Não implementa regra de negócio |
| `api/dependencies` | Injeção de dependências: sessão de DB, usuário autenticado, verificação de permissão | Não acessa banco diretamente |
| `services` | Toda regra de negócio: login, cadastro, troca de senha, emissão/revogação de token, validação de permissão | Não conhece HTTP, não monta `Response` |
| `repositories` | Apenas `SELECT`/`INSERT`/`UPDATE`/`DELETE` via SQLAlchemy | Não contém regra de negócio, não decide o que fazer com o dado |
| `models` | Entidades persistidas (SQLAlchemy ORM) | Não contém lógica de negócio além de validações triviais de integridade |
| `schemas` | Contratos de entrada/saída da API (Pydantic) | Nunca mapeiam 1:1 obrigatoriamente para uma tabela |
| `security` | JWT (geração/validação), hashing de senha, lógica de MFA, abstração de OAuth2 | Não acessa repositórios diretamente |
| `middleware` | Rate limiting, logging estruturado, auditoria, correlação de requisições | Não contém regra de negócio de domínio |
| `core` | Configuração (Pydantic Settings), logging, constantes, primitivas criptográficas | — |
| `exceptions` | Exceções de domínio customizadas e seus handlers HTTP | — |
| `integrations` | Redis, SMTP, providers OAuth externos | — |

---

## 4. Estrutura de Pastas

```text
auth-service/
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth_routes.py
│   │   │   ├── user_routes.py
│   │   │   ├── role_routes.py
│   │   │   ├── permission_routes.py
│   │   │   └── session_routes.py
│   │   ├── dependencies/
│   │   │   ├── auth_dependency.py
│   │   │   ├── db_dependency.py
│   │   │   └── permission_dependency.py
│   │   └── router.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── constants.py
│   │
│   ├── database/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── middleware/
│   │   ├── rate_limit_middleware.py
│   │   ├── logging_middleware.py
│   │   └── audit_middleware.py
│   │
│   ├── models/
│   │   ├── user_model.py
│   │   ├── role_model.py
│   │   ├── permission_model.py
│   │   ├── refresh_token_model.py
│   │   └── session_model.py
│   │
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── role_repository.py
│   │   ├── permission_repository.py
│   │   ├── refresh_token_repository.py
│   │   └── session_repository.py
│   │
│   ├── schemas/
│   │   ├── auth_schema.py
│   │   ├── user_schema.py
│   │   ├── role_schema.py
│   │   ├── permission_schema.py
│   │   └── token_schema.py
│   │
│   ├── security/
│   │   ├── jwt_handler.py
│   │   ├── password_handler.py
│   │   ├── mfa_handler.py
│   │   └── oauth2_handler.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── role_service.py
│   │   ├── permission_service.py
│   │   └── session_service.py
│   │
│   ├── exceptions/
│   │   ├── base_exception.py
│   │   ├── auth_exceptions.py
│   │   ├── user_exceptions.py
│   │   └── exception_handlers.py
│   │
│   ├── integrations/
│   │   ├── redis_client.py
│   │   ├── email_client.py
│   │   └── oauth_providers/
│   │
│   └── main.py
│
├── tests/
│   ├── unit/
│   │   ├── services/
│   │   └── security/
│   ├── integration/
│   │   └── repositories/
│   ├── api/
│   └── conftest.py
│
├── docs/
├── scripts/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

Não existe uma pasta `utils/` genérica — funções auxiliares vivem dentro do módulo que as usa, evitando o "cesto de miscelânea" que esse tipo de pasta tende a virar em projetos maiores.

---

## 5. Modelagem de Dados

### `User`
| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| email | str | unique, indexado |
| hashed_password | str | — |
| full_name | str | — |
| is_active | bool | default `true` |
| is_verified | bool | default `false` |
| is_superuser | bool | default `false` |
| failed_login_attempts | int | default `0` |
| locked_until | datetime \| null | — |
| mfa_enabled | bool | default `false` |
| mfa_secret | str \| null | secret TOTP, só preenchido quando MFA está ativo |
| created_at | datetime | — |
| updated_at | datetime | — |
| deleted_at | datetime \| null | exclusão lógica |

### `Role`
| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| name | str | unique |
| description | str \| null | — |

### `Permission`
| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| code | str | unique (formato `recurso:acao`, ex: `user:create`, `user:delete`) |
| description | str \| null | — |

### Tabelas associativas
- `user_roles` (user_id, role_id)
- `role_permissions` (role_id, permission_id)

### `RefreshToken`
| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| token_hash | str | hash do refresh token, nunca armazenado em texto puro |
| expires_at | datetime | — |
| revoked | bool | default `false` |
| created_at | datetime | — |

### `Session`
| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| device_info | str \| null | user-agent / identificação de dispositivo |
| ip_address | str | — |
| created_at | datetime | — |
| last_active_at | datetime | — |
| revoked | bool | default `false` |

`Role` e `Permission` usam exclusão física (`DELETE`) — diferente de `User`, que usa exclusão lógica (`deleted_at`). A diferença é intencional: excluir uma conta de usuário precisa preservar rastro para auditoria; excluir uma role ou permissão é uma operação de configuração do sistema, sem esse mesmo requisito.

---

## 6. Endpoints da API

### Autenticação (`/api/v1/auth`)
| Método | Rota | Descrição | Autenticado? |
|---|---|---|---|
| POST | `/auth/register` | Cadastro de usuário | Não |
| POST | `/auth/login` | Login, retorna access + refresh token (ou desafio MFA) | Não |
| POST | `/auth/refresh` | Rotaciona refresh token, emite novo par de tokens | Não (usa refresh token) |
| POST | `/auth/logout` | Revoga sessão/refresh token atual | Sim |
| POST | `/auth/logout-all` | Revoga todas as sessões do usuário | Sim |
| POST | `/auth/password/forgot` | Solicita recuperação de senha | Não |
| POST | `/auth/password/reset` | Confirma redefinição de senha | Não (usa token de reset) |
| POST | `/auth/email/confirm` | Confirma e-mail via token | Não |
| POST | `/auth/mfa/enable` | Ativa MFA para o usuário | Sim |
| POST | `/auth/mfa/verify` | Verifica código MFA e conclui o login | Não (usa challenge token) |

### Usuários (`/api/v1/users`)
| Método | Rota | Descrição | Autenticado? |
|---|---|---|---|
| GET | `/users/me` | Retorna o usuário autenticado | Sim |
| PATCH | `/users/me` | Atualiza perfil próprio | Sim |
| PATCH | `/users/me/password` | Altera a própria senha | Sim |
| GET | `/users` | Lista usuários (paginado) | Sim (`user:list`) |
| GET | `/users/{id}` | Detalhe de um usuário | Sim (`user:read`) |
| PATCH | `/users/{id}` | Atualiza um usuário | Sim (`user:update`) |
| DELETE | `/users/{id}` | Exclusão lógica | Sim (`user:delete`) |
| POST | `/users/{id}/activate` | Ativa conta | Sim (`user:update`) |
| POST | `/users/{id}/deactivate` | Desativa conta | Sim (`user:update`) |
| POST | `/users/{id}/roles` | Atribui uma role ao usuário | Sim (`role:assign`) |
| DELETE | `/users/{id}/roles/{role_id}` | Remove uma role do usuário | Sim (`role:assign`) |

### Roles (`/api/v1/roles`)
CRUD completo, protegido por permissões `role:*`, incluindo endpoint para atribuir/remover permissions de uma role (`POST`/`DELETE /roles/{id}/permissions`, exige `permission:assign`).

### Permissions (`/api/v1/permissions`)
CRUD completo, protegido por permissões `permission:*`.

### Sessões (`/api/v1/sessions`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/sessions` | Lista sessões ativas do usuário autenticado |
| DELETE | `/sessions/{id}` | Revoga uma sessão específica (só a própria) |

### Health check (`/api/v1/health`)
Endpoint sem autenticação, usado por orquestradores/load balancers para checagem de disponibilidade — não acessa banco nem Redis, para não gerar falso negativo em caso de instabilidade momentânea de dependências externas.

Todas as respostas de erro seguem um formato padronizado:
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "E-mail ou senha incorretos.",
    "details": null
  }
}
```

Referência completa de todos os endpoints, com a permissão exigida por cada um: `docs/usage-guide.md`.

---

## 7. Fluxos Principais

### Fluxo de Autenticação
```text
Cliente → POST /login → API → AuthService
  → busca usuário → valida senha (comparação em tempo constante via passlib)
  → verifica is_active, is_verified, locked_until
  → se MFA ativo: retorna challenge_token, aguarda /mfa/verify
  → gera Access Token (JWT, curta duração, padrão 15min)
  → gera Refresh Token (longa duração, padrão 7 dias, armazenado como hash)
  → cria registro de Session
  → resposta: { access_token, refresh_token, token_type, expires_in }
```

### Fluxo de Autorização
```text
Cliente → Authorization: Bearer <token> → Dependency
  → extrai token → valida assinatura e expiração
  → carrega usuário → carrega roles → carrega permissions
  → valida se a permission exigida pela rota está presente (ou is_superuser)
  → Endpoint (ou 403)
```

### Rotação de Refresh Token
Ao chamar `/auth/refresh`, o token antigo é **revogado** e um novo par (access + refresh) é emitido. Reuso de um refresh token já revogado dispara a revogação de **todas** as sessões do usuário — proteção contra token replay.

### Rate Limiting e Bloqueio por Força Bruta
Após um número configurável de tentativas de login falhas (padrão 5), a conta é bloqueada por um tempo configurável (padrão 15 minutos), populando `locked_until`. Rate limiting global por IP é aplicado nas rotas de autenticação via middleware + Redis.

---

## 8. Segurança

- Senhas com hash bcrypt (ou argon2), nunca texto puro, nunca logado.
- JWT assinado com HMAC (secret forte vindo de variável de ambiente, validado no startup — nunca hardcoded).
- Refresh tokens armazenados como hash (SHA-256) no banco, nunca em texto puro.
- Todas as entradas validadas via Pydantic antes de chegar à camada de Service.
- Proteção explícita contra: força bruta, credential stuffing, password spraying, token replay, session hijacking, SQL injection (mitigado nativamente pelo uso de ORM com queries parametrizadas), enumeration attacks (mensagens de erro de login não revelam se o e-mail existe).
- Headers de segurança (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, etc.) aplicados via middleware em toda resposta.
- Logs de auditoria estruturados para: login, logout, alteração de senha, criação/alteração/exclusão de usuário, alteração de permissões, revogação de token, tentativas de acesso inválidas — nunca logando senhas ou tokens em texto puro.
- Configuração 100% via variáveis de ambiente, validada na inicialização via Pydantic Settings, com falha rápida (Fail Fast) se uma variável obrigatória estiver ausente ou inválida.

Como este serviço é uma API stateless baseada em Bearer token (sem sessão de cookie), proteções específicas de aplicações com sessão de navegador (CSRF, por exemplo) não se aplicam da mesma forma — a superfície relevante aqui é a de uma API REST autenticada por token, e é essa que guiou as escolhas acima.

---

## 9. Testes

- **Unitários**: cobrindo a camada `services` e `security` com mocks dos repositórios.
- **Integração**: cobrindo `repositories` contra um banco de teste real (container descartável).
- **API**: cobrindo os fluxos completos de autenticação e autorização via `httpx.AsyncClient`, incluindo casos de erro.
- Casos de borda cobertos: login com conta bloqueada, refresh token reutilizado após revogação, acesso a rota protegida sem permissão, expiração de access token, e-mail duplicado no cadastro, tentativa de revogar sessão de outro usuário, escalonamento de privilégio via atribuição de role/permission.

Detalhes de como rodar a suíte localmente: `docs/development-guide.md`.

---

## 10. Infraestrutura

- `docker-compose.yml` orquestrando aplicação (FastAPI/Uvicorn), PostgreSQL e Redis para desenvolvimento local.
- `Dockerfile` multi-stage (build de dependências, ambiente de teste, runtime mínimo).
- Pipeline de CI (`.github/workflows/ci.yml`) executando, em sequência: instalação de dependências, lint (Ruff), checagem de formatação, type-check (Mypy), migração e testes (Pytest) — falhando o build se qualquer etapa falhar.
- `.env.example` listando todas as variáveis necessárias, sem valores reais sensíveis.
- Migrações geridas via Alembic, com a primeira migration criando todo o schema descrito na Seção 5.
- Guia de deploy em produção (VPS, PaaS, banco/Redis gerenciados): `docs/deployment-guide.md`.

---

## 11. Documentação do Projeto

Este documento cobre arquitetura e requisitos técnicos. A documentação está dividida por público-alvo:

| Documento | Para quem |
|---|---|
| `README.md` (raiz) | Visão geral do projeto |
| `docs/development-guide.md` | Quem vai rodar/desenvolver localmente |
| `docs/deployment-guide.md` | Quem vai colocar em produção |
| `docs/integration-guide.md` | Quem vai integrar outra aplicação a este serviço |
| `docs/usage-guide.md` | O que a API faz, do ponto de vista funcional |
| `docs/permissions-reference.md` | Referência detalhada de cada permissão do RBAC |

---

## 12. Definição de Pronto (Definition of Done)

Checklist usado para considerar uma funcionalidade genuinamente concluída, não apenas "código escrito":

- [x] Estrutura de pastas e camadas seguindo a Seção 3/4
- [x] Todos os endpoints relevantes implementados com o contrato da Seção 6
- [x] Regra de dependência entre camadas respeitada, sem violações
- [x] `Services` não importam nada de HTTP; `Repositories` não contêm regra de negócio
- [x] Type hints completos, `mypy --strict` sem erros
- [x] Senhas e refresh tokens nunca em texto puro; nenhum secret hardcoded
- [x] Mensagens de erro de autenticação não vazam informação sobre existência de conta
- [x] Testes cobrindo os casos de borda da Seção 9, suíte passando de fato (não só presente)
- [x] Pipeline de CI válido e verde
- [x] Sem código morto, `TODO` ou placeholders esquecidos
