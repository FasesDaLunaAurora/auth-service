# Auth Service

Microsserviço de **autenticação e autorização**, pronto para produção, construído em **FastAPI + PostgreSQL + SQLAlchemy 2.x (async)**. Ele centraliza login, gestão de sessões, RBAC (roles/permissões) e MFA (TOTP), para que qualquer sistema cliente delegue essas responsabilidades via API em vez de reimplementá-las internamente.

Este README foi escrito para que qualquer pessoa — de quem nunca rodou um projeto FastAPI a quem já mantém sistemas em produção — consiga clonar, configurar e rodar o projeto do zero.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [1. Obtendo o código](#1-obtendo-o-código)
- [2. Configuração do ambiente (.env)](#2-configuração-do-ambiente-env)
- [3. Rodando com Docker (recomendado)](#3-rodando-com-docker-recomendado)
- [4. Rodando localmente sem Docker](#4-rodando-localmente-sem-docker)
- [5. Verificando que está funcionando](#5-verificando-que-está-funcionando)
- [6. Rodando os testes](#6-rodando-os-testes)
- [7. Migrações de banco de dados (Alembic)](#7-migrações-de-banco-de-dados-alembic)
- [8. Populando dados iniciais (seed de permissões)](#8-populando-dados-iniciais-seed-de-permissões)
- [9. Qualidade de código](#9-qualidade-de-código)
- [10. Estrutura de pastas](#10-estrutura-de-pastas)
- [11. Referência de variáveis de ambiente](#11-referência-de-variáveis-de-ambiente)
- [12. Solução de problemas comuns](#12-solução-de-problemas-comuns)
- [13. Contribuindo](#13-contribuindo)
- [14. Decisões de implementação](#14-decisões-de-implementação)

---

## Pré-requisitos

Você só precisa de **uma** das duas colunas abaixo — não das duas.

| Para rodar com Docker (recomendado) | Para rodar localmente sem Docker |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) 24+ | Python 3.11+ |
| Docker Compose (já incluso no Docker Desktop) | PostgreSQL 17 rodando na sua máquina |
| — | Redis rodando na sua máquina |

Para contribuir com código (qualquer um dos dois caminhos), também é útil ter o [Git](https://git-scm.com/downloads) instalado.

---

## 1. Obtendo o código

### Se você recebeu este projeto como um `.zip`

```bash
unzip auth-service.zip
cd auth-service
```

Se você quer versionar este projeto no seu próprio GitHub (recomendado antes de qualquer alteração):

```bash
cd auth-service
git init
git add .
git commit -m "Initial commit: Auth Service"

# Crie um repositório vazio no GitHub primeiro (via github.com/new,
# SEM adicionar README/licença pela interface, para não gerar conflito),
# depois conecte e envie:
git remote add origin https://github.com/SEU_USUARIO/auth-service.git
git branch -M main
git push -u origin main
```

### Se o projeto já está em um repositório Git

```bash
git clone https://github.com/SEU_USUARIO/auth-service.git
cd auth-service
```

> ⚠️ O arquivo `.env` (com seus segredos reais) **nunca** deve ser commitado — o `.gitignore` já está configurado para ignorá-lo. Apenas `.env.example` (sem segredos) fica versionado.

---

## 2. Configuração do ambiente (.env)

Todo o projeto é configurado via variáveis de ambiente, carregadas de um arquivo `.env` na raiz. Copie o exemplo:

```bash
cp .env.example .env
```

Agora abra o `.env` e ajuste **pelo menos** estas variáveis antes de rodar qualquer coisa:

1. **`JWT_SECRET_KEY`** — obrigatório, precisa ter 32+ caracteres e não pode ser um valor óbvio (a aplicação recusa iniciar com placeholders como `changeme`). Gere um valor forte com:
   ```bash
   openssl rand -hex 32
   ```
   Cole o resultado em `JWT_SECRET_KEY=` no `.env`.

2. **`DATABASE_URL`** e **`REDIS_URL`** — os valores padrão do `.env.example` já apontam para os nomes dos serviços do `docker-compose.yml` (`db` e `redis`). Se for rodar **sem Docker**, troque `db`/`redis` por `localhost` (ver [seção 4](#4-rodando-localmente-sem-docker)).

3. **`SMTP_HOST`** — pode deixar em branco em ambiente de desenvolvimento. Sem SMTP configurado, o serviço apenas registra em log os e-mails que enviaria (confirmação de cadastro, reset de senha), em vez de falhar.

Todas as outras variáveis têm valores padrão razoáveis para desenvolvimento — a lista completa e o que cada uma faz está na [seção 11](#11-referência-de-variáveis-de-ambiente).

---

## 3. Rodando com Docker (recomendado)

Com o `.env` configurado (passo anterior), suba tudo com um comando:

```bash
docker compose up --build
```

Isso vai, em ordem:
1. Construir a imagem da aplicação (`docker/Dockerfile`).
2. Subir o PostgreSQL e o Redis, aguardando ambos ficarem saudáveis (`healthcheck`).
3. Rodar as migrações do banco automaticamente (serviço `migrate`).
4. Subir a API em `http://localhost:8000`.

Para rodar em segundo plano (sem travar o terminal):

```bash
docker compose up --build -d
```

Para ver os logs depois:

```bash
docker compose logs -f app
```

Para parar tudo:

```bash
docker compose down
```

Para parar **e apagar os dados do banco** (útil se algo ficou inconsistente e você quer recomeçar do zero):

```bash
docker compose down -v
```

---

## 4. Rodando localmente sem Docker

Use este caminho se você quer depurar o código diretamente na sua IDE sem overhead de container.

### 4.1. Suba PostgreSQL e Redis

Se você não tem Postgres/Redis instalados na máquina, a forma mais rápida é usar o Docker **só para eles** (sem subir a aplicação):

```bash
docker compose up db redis
```

Isso deixa `db` e `redis` escutando em `localhost:5432` e `localhost:6379`.

### 4.2. Ajuste o .env para apontar para localhost

```dotenv
DATABASE_URL=postgresql+asyncpg://auth_service:auth_service@localhost:5432/auth_service
REDIS_URL=redis://localhost:6379/0
```

### 4.3. Crie um ambiente virtual e instale as dependências

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install ".[dev]"             # inclui pytest, ruff, mypy, etc.
```

### 4.4. Rode as migrações

```bash
alembic upgrade head
```

### 4.5. Suba a aplicação

```bash
uvicorn app.main:app --reload
```

A API estará em `http://localhost:8000`, com hot-reload a cada alteração de arquivo.

---

## 5. Verificando que está funcionando

1. **Health check** (não exige autenticação):
   ```bash
   curl http://localhost:8000/api/v1/health
   # {"status":"ok"}
   ```

2. **Documentação interativa (Swagger UI)**: abra `http://localhost:8000/docs` no navegador. Você pode testar todos os endpoints diretamente por lá.

3. **Fluxo completo via linha de comando**:

   Cadastro:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"voce@example.com","full_name":"Seu Nome","password":"SenhaForte1","password_confirm":"SenhaForte1"}'
   ```
   Isso cria o usuário, mas ele começa **não verificado**. Em desenvolvimento (sem SMTP configurado), o token de confirmação aparece no log da aplicação (`docker compose logs -f app` ou no terminal do `uvicorn`), no evento `smtp_not_configured_email_skipped` — copie o token do corpo do e-mail logado e confirme:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/email/confirm \
     -H "Content-Type: application/json" \
     -d '{"token":"COLE_O_TOKEN_AQUI"}'
   ```
   Login:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"voce@example.com","password":"SenhaForte1"}'
   ```
   A resposta traz `access_token`/`refresh_token`. Use o `access_token` em rotas autenticadas:
   ```bash
   curl http://localhost:8000/api/v1/users/me \
     -H "Authorization: Bearer COLE_O_ACCESS_TOKEN_AQUI"
   ```

---

## 6. Rodando os testes

Os testes de integração e de API rodam contra um **banco de dados real** (não um mock) — você precisa de Postgres e Redis acessíveis, com as mesmas variáveis `DATABASE_URL`/`REDIS_URL` do seu `.env`.

```bash
# Se ainda não tiver Postgres/Redis rodando:
docker compose up -d db redis

# Com o ambiente virtual ativado (ver seção 4.3):
pytest
```

Com relatório de cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

Rodando só uma camada de teste:

```bash
pytest tests/unit/            # unitários (services/security, com mocks)
pytest tests/integration/     # repositórios, contra banco real
pytest tests/api/             # fluxos HTTP completos
```

> Os testes criam e destroem as tabelas automaticamente a cada execução (`tests/conftest.py`) — não rode a suíte de testes apontando para o banco de **produção**.

---

## 7. Migrações de banco de dados (Alembic)

A primeira migração (`alembic/versions/0001_initial_schema.py`) já cria todo o schema. Ao alterar um model em `app/models/`, gere uma nova migração:

```bash
alembic revision --autogenerate -m "descreva a alteração aqui"
```

Revise o arquivo gerado em `alembic/versions/` (o autogenerate nem sempre acerta 100%, especialmente em alterações de tipo de coluna), depois aplique:

```bash
alembic upgrade head
```

Para reverter a última migração:

```bash
alembic downgrade -1
```

---

## 8. Populando dados iniciais (seed de permissões)

Um RBAC não é útil sem permissões e uma role de administrador cadastradas. Rode o script de seed uma vez, após a primeira migração:

```bash
python scripts/seed_permissions.py
```

Isso cria, de forma idempotente (pode rodar de novo sem duplicar), todas as permissões definidas em `app/core/constants.py::PermissionCode` e uma role `admin` com todas elas atribuídas. Depois, atribua a role `admin` a um usuário seu via `POST /api/v1/users/{user_id}/roles`, ou marque `is_superuser=True` diretamente no banco para o primeiro usuário (bypassa RBAC completamente).

---

## 9. Qualidade de código

```bash
ruff check .            # lint
ruff check . --fix      # lint com correção automática do que for seguro
ruff format .           # formatação
mypy app                # checagem de tipos estática (modo strict)
```

O pipeline de CI (`.github/workflows/ci.yml`) roda exatamente esses comandos, mais a suíte de testes, a cada `push`/`pull request`.

---

## 10. Estrutura de pastas

```text
auth-service/
├── app/                        # todo o código-fonte da aplicação
│   ├── api/                    # camada HTTP (controllers + injeção de dependências)
│   │   ├── dependencies/       # sessão de DB, usuário autenticado, checagem de permissão
│   │   └── routes/             # um arquivo por recurso (auth, users, roles, permissions, sessions)
│   ├── core/                   # configuração (.env), logging, constantes, primitivas de segurança
│   ├── database/               # engine SQLAlchemy, base declarativa, fábrica de sessões
│   ├── exceptions/             # exceções de domínio e sua tradução para respostas HTTP
│   ├── integrations/           # clientes de serviços externos (SMTP, Redis, OAuth2)
│   ├── middleware/             # rate limiting, logging estruturado, auditoria de segurança
│   ├── models/                 # entidades do banco (SQLAlchemy)
│   ├── repositories/           # única camada que fala SQL/ORM diretamente
│   ├── schemas/                # contratos de entrada/saída da API (Pydantic)
│   ├── security/                # JWT, hashing de senha, MFA (TOTP), OAuth2 — regras de domínio
│   ├── services/                # toda a regra de negócio (a camada mais importante para ler primeiro)
│   └── main.py                  # ponto de entrada: monta middlewares, rotas e handlers de erro
│
├── alembic/                     # migrações de banco de dados
│   └── versions/                 # um arquivo por migração, gerado via `alembic revision`
│
├── tests/                        # suíte de testes, espelhando a estrutura de `app/`
│   ├── unit/                      # services/security com repositórios mockados (rápidos, sem DB)
│   ├── integration/                # repositórios contra um banco real
│   └── api/                        # fluxos HTTP de ponta a ponta
│
├── docker/
│   └── Dockerfile                 # build multi-stage da imagem de produção
│
├── docs/                          # documentação estendida do projeto (ver docs/README.md)
├── scripts/                       # scripts utilitários de operação (ver scripts/README.md)
│
├── .env.example                   # modelo de variáveis de ambiente (sem segredos reais)
├── .gitignore
├── docker-compose.yml              # orquestra app + PostgreSQL + Redis para desenvolvimento
├── pyproject.toml                  # dependências, config do Ruff/Mypy/Pytest
└── README.md                       # este arquivo
```

**Por onde começar a ler o código**, se você é novo no projeto: `app/services/` primeiro (é onde a lógica de negócio vive), depois `app/api/routes/` para ver como cada endpoint usa os services, e só depois `app/repositories/`/`app/models/` para entender a persistência.

### Sobre as pastas docs/ e scripts/

Essas duas pastas fazem parte da estrutura do projeto (para acomodar crescimento futuro), mas propositalmente não vêm cheias de conteúdo especulativo:

- **`docs/`** — reservada para documentação estendida que não cabe num README (diagramas de arquitetura, ADRs — *Architecture Decision Records* —, coleções do Postman/Insomnia, runbooks de incidente). Veja `docs/README.md` para o que colocar aqui conforme o projeto crescer.
- **`scripts/`** — reservada para scripts operacionais de manutenção, rodados manualmente ou via cron/job agendado (fora do ciclo de requisição HTTP). Já vem com `scripts/seed_permissions.py` funcional (seção 8) — veja `scripts/README.md` para a lista completa e convenções para adicionar novos scripts.

---

## 11. Referência de variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `APP_NAME` | Não | `auth-service` | Nome da aplicação (aparece nos logs). |
| `APP_ENV` | Não | `development` | `development`, `staging`, `production` ou `test`. Em `production`, `/docs`/`/redoc`/`/openapi.json` ficam desativados. |
| `APP_DEBUG` | Não | `false` | Ativa logs mais verbosos. |
| `APP_HOST` / `APP_PORT` | Não | `0.0.0.0` / `8000` | Endereço em que o Uvicorn escuta. |
| `API_V1_PREFIX` | Não | `/api/v1` | Prefixo de todas as rotas versionadas. |
| `DATABASE_URL` | **Sim** | — | URL assíncrona do Postgres, formato `postgresql+asyncpg://usuario:senha@host:5432/banco`. |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` / `DATABASE_POOL_TIMEOUT_SECONDS` | Não | `10` / `20` / `30` | Tuning do pool de conexões. |
| `DATABASE_ECHO` | Não | `false` | Se `true`, loga todo SQL executado (só para depuração local). |
| `REDIS_URL` | **Sim** | — | URL do Redis, formato `redis://host:6379/0`. |
| `JWT_SECRET_KEY` | **Sim** | — | Secret de assinatura dos tokens. Mín. 32 caracteres, não pode ser um placeholder óbvio. |
| `JWT_ALGORITHM` | Não | `HS256` | Algoritmo de assinatura JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Não | `15` | Validade do access token. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Não | `7` | Validade do refresh token. |
| `EMAIL_TOKEN_EXPIRE_HOURS` | Não | `24` | Validade do token de confirmação de e-mail. |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | Não | `30` | Validade do token de redefinição de senha. |
| `PASSWORD_HASH_SCHEME` | Não | `bcrypt` | `bcrypt` ou `argon2`. |
| `BCRYPT_ROUNDS` | Não | `12` | Custo computacional do bcrypt. |
| `MAX_FAILED_LOGIN_ATTEMPTS` | Não | `5` | Tentativas de login falhas antes de bloquear a conta. |
| `ACCOUNT_LOCKOUT_MINUTES` | Não | `15` | Duração do bloqueio por força bruta. |
| `RATE_LIMIT_AUTH_REQUESTS` / `RATE_LIMIT_AUTH_WINDOW_SECONDS` | Não | `10` / `60` | Limite de requisições por IP nas rotas `/auth/*`. |
| `MFA_ISSUER_NAME` | Não | `AuthService` | Nome exibido no app autenticador (Google Authenticator, etc). |
| `SMTP_HOST` | Não | *(vazio)* | Se vazio, e-mails só são logados, não enviados de verdade. |
| `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` / `SMTP_USE_TLS` | Não | ver `.env.example` | Configuração do servidor SMTP. |
| `CORS_ALLOWED_ORIGINS` | Não | `["http://localhost:3000"]` | Lista JSON de origens permitidas. |
| `LOG_LEVEL` | Não | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`. |
| `LOG_JSON` | Não | `true` | Se `false`, logs saem em texto legível em vez de JSON (útil rodando localmente sem Docker). |

---

## 12. Solução de problemas comuns

**"A aplicação não inicia, erro de ValidationError no Settings"**
Alguma variável obrigatória (`DATABASE_URL`, `REDIS_URL` ou `JWT_SECRET_KEY`) está ausente ou inválida no `.env`. Revise a seção 2.

**"docker compose up fica travado em db sem ficar saudável"**
A porta `5432` já pode estar em uso por outro Postgres na sua máquina. Pare o outro serviço ou mude o mapeamento de porta em `docker-compose.yml`.

**"Erro de conexão recusada ao rodar localmente sem Docker"**
Confira se trocou `db`/`redis` por `localhost` no `.env` (seção 4.2) — os nomes `db`/`redis` só resolvem dentro da rede do Docker Compose.

**"Recebo 401/403 em rotas que deveriam funcionar"**
Confira se o usuário está com `is_verified=True` (login exige confirmação de e-mail) e, para rotas administrativas, se ele tem a permissão RBAC necessária (seção 8) ou `is_superuser=True`.

**"Alterei um model e o Alembic não detectou a mudança"**
Confirme que o novo model está importado em `alembic/env.py` — sem o import, o SQLAlchemy não sabe que a tabela existe.

---

## 13. Contribuindo

Contribuições são bem-vindas. Fluxo sugerido:

1. Abra uma *issue* descrevendo o problema/melhoria antes de codar, para alinhar escopo.
2. Crie um branch a partir de `main`: `git checkout -b minha-feature`.
3. Rode `ruff check .`, `ruff format .` e `mypy app` antes de commitar — o CI vai rejeitar o PR se algum falhar.
4. Adicione/atualize testes para qualquer mudança de comportamento (`pytest` precisa passar).
5. Abra o Pull Request descrevendo o que mudou e por quê.

---

## 14. Decisões de implementação

Este projeto foi gerado a partir de uma especificação técnica detalhada. Onde a especificação era ambígua, incompleta ou internamente contraditória, a decisão tomada foi documentada diretamente no arquivo afetado (comentários "Nota de decisão") e resumida abaixo:

1. **`core/security.py` vs. pacote `security/`**: primitivas puras (passlib/jose/hashlib) ficam em `core/security.py`; a camada de domínio de segurança (`JWTHandler`, `PasswordHandler`, `MFAHandler`, `OAuth2Handler`) fica em `security/`.
2. **Campos de MFA ausentes na modelagem de dados original**: adicionados `mfa_enabled`/`mfa_secret` a `User`, exigidos pelos endpoints `/auth/mfa/*` mas ausentes na tabela original da especificação.
3. **Schemas de `Session`**: colocados em `auth_schema.py` (não existe `session_schema.py` na árvore de pastas original).
4. **Componentes "adiantados"**: `refresh_token_repository.py`, `session_repository.py`, `permission_service.py`, `session_service.py`, `email_client.py`, `redis_client.py` e `scripts/seed_permissions.py` não tinham etapa própria no cronograma original, mas são pré-requisitos diretos de outros componentes — gerados assim que necessários.
5. **MFA (TOTP)** implementado só com a *standard library* (`hmac`, `base64`, `struct`), sem novas dependências.
6. **Claim `sid`** (session id) adicionada aos tokens, para que `POST /auth/logout` saiba qual sessão revogar sem exigir esse dado no corpo da requisição.
7. **`Role`/`Permission`** usam exclusão física; `User` usa exclusão lógica (`deleted_at`).
8. **Regra adicional**: um usuário não pode desativar/excluir a própria conta via `/users/{id}`.
9. **Paths de atribuição RBAC** (`/users/{id}/roles`, `/roles/{id}/permissions`) definidos por não estarem fixados na especificação original.
10. **Endpoint de health check** (`GET /api/v1/health`) adicionado por necessidade operacional.
11. **OAuth2** implementado como abstração genérica (Authorization Code Flow), sem provider concreto, por não haver endpoint OAuth definido na especificação original.
