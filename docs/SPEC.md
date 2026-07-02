# Especificação Técnica — Auth Service
### Documento de instruções para geração de projeto via IA (uso em pesquisa de TCC)

---

## ⚠️ Como usar este documento

Este documento é uma **especificação técnica completa e fechada** de um microsserviço de autenticação e autorização. Ele foi escrito para ser entregue a uma IA generativa (modelo de linguagem em formato de chat, sem acesso a ferramentas de execução de código) com o objetivo de gerar a implementação completa do projeto, em texto, para posterior comparação acadêmica com uma versão desenvolvida manualmente por um humano.

**Instruções para a IA que receber este documento:**

1. Implemente **exatamente** o que está especificado — nomes de pastas, arquivos, classes, schemas e fluxos devem seguir esta especificação à risca, sem omitir camadas nem simplificar a arquitetura.
2. Quando algo não estiver explicitamente definido (ex: um detalhe de validação não mencionado), tome a decisão mais alinhada com as boas práticas de engenharia citadas na Seção 1 e declare explicitamente a decisão tomada e por quê.
3. Gere o código em blocos, organizado por camada (Models → Schemas → Repositories → Services → API → Security → Middleware → Core → Testes), apresentando o conteúdo completo de cada arquivo definido na estrutura de pastas (Seção 4).
4. Não pule etapas por brevidade. Se o volume total for grande, avise que continuará em mensagens subsequentes, mas gere todos os arquivos especificados.
5. Ao final, gere também o `README.md`, `.env.example`, `docker-compose.yml`, `requirements.txt`/`pyproject.toml` e o pipeline de CI (`.github/workflows/`).

---

## 1. Contexto e Objetivo do Projeto

Você deve construir o **Auth Service**: um microsserviço de autenticação e autorização, desacoplado de qualquer aplicação cliente, construído em **Python com FastAPI**, **PostgreSQL** como banco de dados e **SQLAlchemy 2.x** como ORM, com migrações via **Alembic**.

O objetivo do serviço é centralizar **autenticação**, **autorização** e **gestão de usuários**, de modo que qualquer sistema cliente possa delegar essas responsabilidades a este serviço via API, sem precisar reimplementar login, controle de sessão ou RBAC internamente.

O projeto deve ser tratado como **pronto para produção e reutilizável como template** — não como um protótipo ou MVP. Isso significa: sem TODOs, sem placeholders de "implementar depois", com tratamento de erro completo e testes cobrindo os fluxos críticos.

### Princípios obrigatórios de engenharia

A implementação deve respeitar, sem exceção:

- **Clean Architecture** com separação estrita de camadas (ver Seção 3)
- **SOLID**
- **Dependency Injection** (via sistema de dependências do FastAPI)
- **Repository Pattern** — acesso a dados isolado em repositórios
- **Service Layer** — toda regra de negócio centralizada em services
- **Programação defensiva** e **Fail Fast / Fail Secure**
- **Security by Design** — segurança não é uma camada adicionada depois, é parte de cada decisão
- Recomendações **OWASP** para APIs (OWASP API Security Top 10)
- Tipagem forte em 100% do código (type hints completos, validável com Mypy)
- Código testável: nenhuma camada deve impedir testes unitários isolados das demais

### Regra de dependência entre camadas (não pode ser violada)

```text
API → Services → Repositories → Database
```

- Camadas inferiores **nunca** importam ou conhecem camadas superiores.
- `Repositories` nunca conhecem `Services`.
- `Services` nunca conhecem detalhes de HTTP (nunca importam `Request`, `Response`, `HTTPException` diretamente — exceções de domínio são traduzidas para HTTP apenas na camada de API).
- `Schemas` (Pydantic) nunca são usados como entidades de banco; `Models` (SQLAlchemy) nunca são expostos diretamente na API.

---

## 2. Stack Tecnológica (obrigatória, sem substituições)

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
| JWT | python-jose ou pyjwt | — |
| Testes | Pytest + pytest-asyncio + httpx (AsyncClient) | — |
| Lint/Format | Ruff | — |
| Type checking | Mypy | — |
| Containerização | Docker + Docker Compose | — |
| CI | GitHub Actions | — |
| Cache/Rate limiting | Redis | — |

Não substitua nenhuma tecnologia desta lista por equivalentes (ex: não usar Django, não usar MongoDB, não usar Tortoise ORM). O objetivo da comparação no TCC depende da stack ser idêntica entre as duas versões.

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
| `security` | JWT (geração/validação), hashing de senha, lógica de MFA, OAuth2 | Não acessa repositórios diretamente |
| `middleware` | Rate limiting, logging estruturado, auditoria, correlação de requisições | Não contém regra de negócio de domínio |
| `core` | Configuração (Pydantic Settings), logging, constantes | — |
| `exceptions` | Exceções de domínio customizadas e seus handlers HTTP | — |
| `integrations` | Redis, SMTP, providers OAuth externos | — |

---

## 4. Estrutura de Pastas (gerar exatamente esta árvore)

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
│   │   ├── session.py
│   │   └── migrations.py
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
│   ├── utils/
│   │   ├── validators.py
│   │   └── formatters.py
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
│   │   ├── test_auth_routes.py
│   │   ├── test_user_routes.py
│   │   └── test_role_routes.py
│   └── conftest.py
│
├── docker/
│   └── Dockerfile
│
├── docs/
│
├── scripts/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 5. Modelagem de Dados (Entidades obrigatórias)

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
| code | str | unique (ex: `user:create`, `user:delete`) |
| description | str \| null | — |

### Tabelas associativas
- `user_roles` (user_id, role_id)
- `role_permissions` (role_id, permission_id)

### `RefreshToken`
| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| token_hash | str | hash do refresh token, nunca armazenar em texto puro |
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

---

## 6. Endpoints da API (contrato obrigatório)

### Autenticação (`/api/v1/auth`)
| Método | Rota | Descrição | Autenticado? |
|---|---|---|---|
| POST | `/auth/register` | Cadastro de usuário | Não |
| POST | `/auth/login` | Login, retorna access + refresh token | Não |
| POST | `/auth/refresh` | Rotaciona refresh token, emite novo access token | Não (usa refresh token) |
| POST | `/auth/logout` | Revoga sessão/refresh token atual | Sim |
| POST | `/auth/logout-all` | Revoga todas as sessões do usuário | Sim |
| POST | `/auth/password/forgot` | Solicita recuperação de senha | Não |
| POST | `/auth/password/reset` | Confirma redefinição de senha | Não (usa token de reset) |
| POST | `/auth/email/confirm` | Confirma e-mail via token | Não |
| POST | `/auth/mfa/enable` | Ativa MFA para o usuário | Sim |
| POST | `/auth/mfa/verify` | Verifica código MFA no login | Não (parte do fluxo de login) |

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

### Roles e Permissions (`/api/v1/roles`, `/api/v1/permissions`)
CRUD completo em ambos, protegido por permissões `role:*` e `permission:*`, incluindo endpoints para atribuir/remover roles de um usuário e permissions de uma role.

### Sessões (`/api/v1/sessions`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/sessions` | Lista sessões ativas do usuário autenticado |
| DELETE | `/sessions/{id}` | Revoga uma sessão específica |

Todas as respostas de erro devem seguir um formato padronizado:
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "E-mail ou senha incorretos.",
    "details": null
  }
}
```

---

## 7. Fluxos Obrigatórios

### Fluxo de Autenticação
```text
Cliente → POST /login → API → AuthenticationService
  → busca usuário → valida senha (constant-time compare via passlib)
  → verifica is_active, is_verified, locked_until
  → gera Access Token (JWT, curta duração, ex: 15min)
  → gera Refresh Token (longa duração, ex: 7 dias, armazenado como hash)
  → cria registro de Session
  → resposta: { access_token, refresh_token, token_type, expires_in }
```

### Fluxo de Autorização
```text
Cliente → Authorization: Bearer <token> → Middleware/Dependency
  → extrai token → valida assinatura e expiração
  → carrega usuário → carrega roles → carrega permissions
  → valida se a permission exigida pela rota está presente
  → Endpoint (ou 403 Forbidden)
```

### Rotação de Refresh Token
Ao chamar `/auth/refresh`, o token antigo deve ser **revogado** e um novo par (access + refresh) emitido. Reuso de um refresh token já revogado deve disparar revogação de **todas** as sessões do usuário (proteção contra token replay).

### Rate Limiting e Bloqueio por Força Bruta
Após N tentativas de login falhas (configurável via `.env`, padrão 5), bloquear a conta por tempo configurável (padrão 15 minutos), populando `locked_until`. Rate limiting global por IP também deve ser aplicado nas rotas de autenticação via middleware + Redis.

---

## 8. Segurança (requisitos não negociáveis)

- Senhas: hash com bcrypt ou argon2, nunca texto puro, nunca logado.
- JWT: assinado com algoritmo assimétrico ou HMAC com secret forte vindo de variável de ambiente; nunca hardcoded.
- Refresh tokens: armazenados como hash no banco, nunca em texto puro.
- Todas as entradas validadas via Pydantic antes de chegar à camada de Service.
- Proteção explícita contra: Brute Force, Credential Stuffing, Password Spraying, Token Replay, Session Hijacking, CSRF, XSS, SQL Injection (mitigado nativamente pelo uso de ORM com queries parametrizadas), Enumeration Attacks (mensagens de erro de login não devem revelar se o e-mail existe).
- Headers de segurança (ex: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`) aplicados via middleware.
- Logs de auditoria para: login, logout, alteração de senha, criação/alteração/exclusão de usuário, alteração de permissões, revogação de token, tentativas de acesso inválidas — sem nunca logar senhas ou tokens em texto puro.
- Configuração 100% via variáveis de ambiente (`.env`), validada na inicialização via Pydantic Settings (`core/config.py`), com **falha rápida** (Fail Fast) se uma variável obrigatória estiver ausente.

---

## 9. Testes (obrigatório)

- **Unitários**: cobrindo toda a camada `services` e `security` com mocks dos repositórios.
- **Integração**: cobrindo `repositories` contra um banco de teste real (ou container descartável).
- **API**: cobrindo os fluxos completos de autenticação e autorização via `httpx.AsyncClient`, incluindo casos de erro (credenciais inválidas, token expirado, permissão insuficiente, conta bloqueada).
- Casos de borda obrigatórios a testar: login com conta bloqueada, refresh token reutilizado após revogação, acesso a rota protegida sem permissão, expiração de access token, e-mail duplicado no cadastro.

---

## 10. Infraestrutura e Entrega

- `docker-compose.yml` orquestrando: aplicação (FastAPI/Uvicorn), PostgreSQL e Redis.
- `Dockerfile` multi-stage, imagem final mínima (ex: `python:3.11-slim`).
- Pipeline de CI (`.github/workflows/ci.yml`) executando, em sequência: instalação de dependências, lint (Ruff), type-check (Mypy), testes (Pytest) — falhando o build se qualquer etapa falhar.
- `.env.example` listando todas as variáveis necessárias, sem valores reais sensíveis.
- Migrações geridas via Alembic, com a primeira migration criando todo o schema descrito na Seção 5.

---

## 11. Entregáveis Esperados (o que a IA deve gerar)

1. Todo o código-fonte da árvore descrita na Seção 4, arquivo por arquivo, completo (sem trechos truncados ou `# ...`).
2. `README.md` do projeto final (estilo documentação de produto pronto para uso).
3. `.env.example`, `docker-compose.yml`, `Dockerfile`, `pyproject.toml`.
4. Pipeline de CI (`.github/workflows/ci.yml`).
5. Suíte de testes conforme Seção 9.
6. Um changelog breve, ao final da resposta, listando qualquer decisão de implementação que tenha sido necessária além do que esta especificação definiu explicitamente (para fins de análise comparativa no TCC).

---

## 12. Checklist de Avaliação (uso pós-geração, para comparação no TCC)

> Esta seção não é parte das instruções para a IA geradora — é para uso seu, ao avaliar o output gerado em comparação com o seu projeto desenvolvido manualmente.

### 12.1 Fidelidade à especificação
- [ ] Estrutura de pastas gerada corresponde exatamente à Seção 4
- [ ] Todas as entidades da Seção 5 foram implementadas com os campos especificados
- [ ] Todos os endpoints da Seção 6 foram implementados com os métodos/rotas corretos
- [ ] Regra de dependência entre camadas (`API → Services → Repositories → DB`) foi respeitada sem violações
- [ ] Nenhuma tecnologia da Seção 2 foi substituída

### 12.2 Qualidade arquitetural
- [ ] `Services` realmente não importam nada de HTTP (`Request`, `Response`, `HTTPException`)
- [ ] `Repositories` realmente não contêm regra de negócio
- [ ] Há separação real entre `Models` (ORM) e `Schemas` (Pydantic), sem reuso indevido
- [ ] Tratamento de exceções é centralizado (não há `try/except` espalhado de forma ad-hoc nas rotas)
- [ ] Type hints presentes e coerentes em praticamente 100% do código

### 12.3 Segurança
- [ ] Senhas e refresh tokens armazenados como hash, nunca em texto puro
- [ ] Mensagens de erro de login não vazam se o e-mail existe (proteção contra enumeration)
- [ ] Rotação e revogação de refresh token implementada corretamente, incluindo detecção de reuso
- [ ] Rate limiting e bloqueio por tentativas falhas realmente implementados (não apenas mencionados)
- [ ] Nenhum secret hardcoded no código

### 12.4 Testes e CI
- [ ] Testes cobrem os casos de borda listados na Seção 9
- [ ] Testes realmente passam (validar executando, não apenas pela presença do arquivo)
- [ ] Pipeline de CI gerado é válido e executável
- [ ] Cobertura de testes nas camadas `services` e `security` é proporcional ao peso de regra de negócio que carregam

### 12.5 Qualidade geral / "code smell"
- [ ] Ausência de código morto, `TODO`, placeholders ou funções vazias
- [ ] Nomenclatura consistente entre os arquivos (sem misturar convenções)
- [ ] Documentação inline (docstrings) presente nos pontos de decisão não triviais (ex: lógica de rotação de token)
- [ ] Tratamento de concorrência/race condition considerado nos pontos sensíveis (ex: rotação de refresh token, contagem de tentativas de login)

### 12.6 Critério comparativo central (para a análise do TCC)
- [ ] Diferença de tempo de desenvolvimento (humano vs. tempo de geração + revisão da IA)
- [ ] Diferença na quantidade de retrabalho necessário até o código compilar/rodar/passar os testes
- [ ] Diferença na aderência à arquitetura pedida (desvios não declarados pela IA vs. desvios declarados no changelog da Seção 11.6)
- [ ] Diferença na cobertura real de segurança (itens da Seção 12.3 atendidos de fato, não apenas citados em texto)
- [ ] Qualidade do changelog/justificativas dadas pela IA quando teve que tomar decisões não especificadas
