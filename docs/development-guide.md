# Guia de Desenvolvimento Local

Este guia cobre tudo que você precisa para rodar, testar e contribuir com o projeto no seu próprio computador. Para colocar em produção, veja `docs/deployment-guide.md`.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
  - [Opção A: Docker Desktop](#opção-a-docker-desktop)
  - [Opção B: Docker Engine (Linux, sem Desktop)](#opção-b-docker-engine-linux-sem-desktop)
  - [Opção C: Podman](#opção-c-podman)
  - [Configurando autocomplete no editor (opcional)](#configurando-autocomplete-no-editor-opcional)
- [1. Obtendo o código](#1-obtendo-o-código)
- [2. Configuração do ambiente (.env)](#2-configuração-do-ambiente-env)
- [3. Rodando a aplicação](#3-rodando-a-aplicação)
  - [Quando preciso reconstruir a imagem (--build)?](#quando-preciso-reconstruir-a-imagem---build)
- [4. Verificando que está funcionando](#4-verificando-que-está-funcionando)
- [5. Rodando os testes](#5-rodando-os-testes)
  - [Salvando a saída dos testes em arquivo](#salvando-a-saída-dos-testes-em-arquivo)
- [6. Migrações de banco de dados (Alembic)](#6-migrações-de-banco-de-dados-alembic)
- [7. Populando dados iniciais (seed de permissões)](#7-populando-dados-iniciais-seed-de-permissões)
- [8. Qualidade de código](#8-qualidade-de-código)
  - [Checklist antes de commitar](#checklist-antes-de-commitar)
- [9. Referência de variáveis de ambiente](#9-referência-de-variáveis-de-ambiente)
- [10. Solução de problemas comuns](#10-solução-de-problemas-comuns)
- [11. Decisões de design ao longo do desenvolvimento](#11-decisões-de-design-ao-longo-do-desenvolvimento)

---

## Pré-requisitos

O projeto roda **exclusivamente em containers**,  não há suporte a instalação local do Python/PostgreSQL/Redis direto no sistema operacional. Isso garante que o ambiente de qualquer pessoa (independente de sistema operacional ou versões instaladas) seja idêntico ao de produção.

Escolha **uma** das três opções abaixo, dependendo do seu sistema:

### Opção A: Docker Desktop

A opção mais comum em Windows e macOS.

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 24+ (já inclui o Compose)

Todos os comandos deste guia usam `docker compose` — funcionam direto com essa opção, sem tradução nenhuma.

### Opção B: Docker Engine (Linux, sem Desktop)

Se você está em um servidor ou distribuição Linux sem interface gráfica, instale o Engine diretamente, sem o Desktop:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # evita precisar de sudo em todo comando
```

O plugin `docker compose` já vem incluso nas versões recentes do Engine. Os comandos deste guia funcionam exatamente iguais.

### Opção C: Podman

Mais leve que o Docker Desktop, boa opção se seu computador tem pouca RAM sobrando ou você prefere uma ferramenta rootless por padrão.

- [Podman](https://podman.io/docs/installation) 5+
- `podman-compose` (`pip install podman-compose`) — o Podman não tem um subcomando `compose` funcional sozinho, por isso essa dependência extra

**Configuração (uma vez só, Windows/macOS — no Linux nativo o Podman já roda direto):**
```powershell
podman machine init
podman machine start
pip install podman-compose
```

**Uso no dia a dia:** troque `docker compose` por `podman-compose` (sem espaço, com hífen) em **todo comando deste guia**. Exemplos:

| Este guia diz | Com Podman, rode |
|---|---|
| `docker compose up --build` | `podman-compose up --build` |
| `docker compose up -d` | `podman-compose up -d` |
| `docker compose logs -f app` | `podman-compose logs -f app` |
| `docker compose down` / `down -v` | `podman-compose down` / `down -v` |
| `docker compose run --rm migrate` | `podman-compose run --rm migrate` |
| `docker compose --profile test run --rm test <comando>` | `podman-compose run --rm test <comando>` |

**Duas particularidades do `podman-compose` para ficar de olho** (testado na versão 1.6.0):

1. **`profiles:` pode não ser respeitado**, o serviço `test` usa `profiles: [test]` justamente para não subir junto no `up` normal. Se ele subir mesmo assim, pare-o manualmente (`podman-compose stop test`) ou suba só os serviços que quer, nomeando-os: `podman-compose up --build db redis migrate app`.
2. **`depends_on: condition: service_healthy` pode ser menos confiável** que no Docker Compose — se `migrate`/`app` tentarem subir antes do Postgres/Redis estarem prontos, suba o banco primeiro e aguarde alguns segundos:
   ```powershell
   podman-compose up -d db redis
   # aguarde alguns segundos
   podman-compose up --build migrate app
   ```

Se encontrar outro comportamento diferente do documentado aqui, é provável que seja particularidade de versão do `podman-compose`,  vale registrar como *issue* no repositório.

### Configurando autocomplete no editor (opcional)

Como o projeto roda inteiramente em container, seu sistema operacional não tem `fastapi`, `sqlalchemy` e as demais dependências instaladas, então seu editor (VS Code, PyCharm, etc.) provavelmente vai mostrar avisos do tipo `Import "fastapi" could not be resolved`. **Isso não afeta a aplicação rodando** — é só o editor não tendo onde procurar as bibliotecas para autocomplete/checagem de tipos.

Se quiser eliminar esses avisos, crie um ambiente virtual **só para o editor usar como referência** — ele nunca roda a aplicação nem se conecta a nada, é puramente para o autocomplete conseguir ler as bibliotecas:

```bash
python -m venv .venv-editor
```

Ative:
```powershell
# Windows (PowerShell)
.venv-editor\Scripts\activate
```
```bash
# Linux / macOS
source .venv-editor/bin/activate
```

Instale as dependências (incluindo as de desenvolvimento — pytest, ruff, mypy):
```bash
pip install ".[dev]"
```

No VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → escolha o interpretador dentro de `.venv-editor`.

Esse passo é **totalmente opcional** e não usa recursos do computador além de espaço em disco (~300–400MB) — diferente da VM do Docker/Podman, que consome CPU/RAM enquanto estiver rodando.

---

## 1. Obtendo o código

```bash
git clone https://github.com/<seu-usuario>/auth-service.git
cd auth-service
```

> O arquivo `.env` (com seus segredos reais) **nunca** deve ser commitado — o `.gitignore` já está configurado para ignorá-lo. Apenas `.env.example` (sem segredos) fica versionado.

---

## 2. Configuração do ambiente (.env)

Todo o projeto é configurado via variáveis de ambiente, carregadas de um arquivo `.env` na raiz.

```bash
cp .env.example .env
```

Ajuste **pelo menos** estas variáveis antes de rodar qualquer coisa:

1. **`JWT_SECRET_KEY`** — obrigatório, precisa ter 32+ caracteres e não pode ser um valor óbvio (a aplicação recusa iniciar com placeholders como `changeme`). Gere um valor forte com:
   ```bash
   openssl rand -hex 32
   ```

2. **`DATABASE_URL`** e **`REDIS_URL`** — os valores padrão do `.env.example` já apontam para os nomes dos serviços do `docker-compose.yml` (`db` e `redis`). Não altere isso — esses nomes só resolvem dentro da rede interna criada pelo Compose.

3. **`SMTP_HOST`** — pode deixar em branco em desenvolvimento. Sem SMTP configurado, o serviço apenas registra em log os e-mails que enviaria, em vez de falhar.

Todas as outras variáveis têm valores padrão razoáveis — lista completa na [seção 9](#9-referência-de-variáveis-de-ambiente).

---

## 3. Rodando a aplicação

```bash
docker compose up --build
```

Isso vai, em ordem:
1. Construir a imagem da aplicação (`Dockerfile`, multi-stage).
2. Subir PostgreSQL e Redis, aguardando ambos ficarem saudáveis.
3. Rodar as migrações do banco automaticamente (serviço `migrate`).
4. Subir a API em `http://localhost:8000`.

Em segundo plano: `docker compose up --build -d`. Ver logs depois: `docker compose logs -f app`. Parar: `docker compose down`. Parar e apagar dados do banco: `docker compose down -v`.

### Quando preciso reconstruir a imagem (`--build`)?

Os serviços `app`, `migrate` e `test` montam `app/`, `alembic/` e `scripts/` do seu computador direto dentro do container — e `test` também monta `tests/`. Isso significa que, no dia a dia, **editar esses arquivos e salvar já é suficiente**: `app` roda com `--reload`, e `migrate`/`test` sempre leem a versão mais recente na hora que rodam.

| Você alterou... | Precisa de `--build`? |
|---|---|
| Qualquer arquivo em `app/`, `tests/`, `alembic/` ou `scripts/` | **Não** |
| `pyproject.toml` (dependência nova) | **Sim** — a dependência só existe dentro da imagem construída |
| `Dockerfile` | **Sim** |
| `docker-compose.yml` | Depende: mudanças em `volumes`/`command`/`ports`/`environment` não precisam; mudanças que afetam o build (`target:`) precisam |
| `.env` | **Não** — reinicie o container (`docker compose restart app`) |

Na dúvida, `docker compose up --build` sempre funciona (o cache evita que seja lento na maioria das vezes).

---

## 4. Verificando que está funcionando

**Health check:**
```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

**Documentação interativa (Swagger UI):** `http://localhost:8000/docs`.

**Fluxo completo via linha de comando:**

```bash
# Cadastro
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"voce@example.com","full_name":"Seu Nome","password":"SenhaForte1","password_confirm":"SenhaForte1"}'
```

O usuário criado começa **não verificado**. Sem SMTP configurado, o token de confirmação aparece no log da aplicação (evento `smtp_not_configured_email_skipped`):

```bash
curl -X POST http://localhost:8000/api/v1/auth/email/confirm \
  -H "Content-Type: application/json" \
  -d '{"token":"COLE_O_TOKEN_AQUI"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"voce@example.com","password":"SenhaForte1"}'

curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer COLE_O_ACCESS_TOKEN_AQUI"
```

---

## 5. Rodando os testes

Os testes de integração e de API rodam contra um **banco de dados real** (não um mock). O serviço `test` do Compose já vem com `pytest`, `ruff` e `mypy` instalados, atrás de um [profile](https://docs.docker.com/compose/how-tos/profiles/) — não sobe junto com `docker compose up` normal.

```bash
docker compose up -d db redis
docker compose --profile test run --rm test
```

Rodando só uma camada:
```bash
docker compose --profile test run --rm test pytest tests/unit/
docker compose --profile test run --rm test pytest tests/integration/
docker compose --profile test run --rm test pytest tests/api/
```

> Os testes criam e destroem as tabelas automaticamente a cada execução (`tests/conftest.py`) — não aponte `DATABASE_URL` para produção ao rodar testes.

### Salvando a saída dos testes em arquivo

Útil quando há várias falhas e o buffer do terminal não é suficiente:

```powershell
# Windows (PowerShell)
docker compose --profile test run --rm test 2>&1 | Tee-Object -FilePath pytest_output.txt
```
```bash
# Linux / macOS
docker compose --profile test run --rm test 2>&1 | tee pytest_output.txt
```

Ver só o final:
```powershell
Get-Content pytest_output.txt -Tail 30
```
```bash
tail -n 30 pytest_output.txt
```

> No Windows/PowerShell, `Tee-Object` grava em UTF-16 por padrão — converta a codificação se for abrir o arquivo em outra ferramenta que espere UTF-8.

---

## 6. Migrações de banco de dados (Alembic)

A primeira migração já cria todo o schema e roda automaticamente ao subir o projeto. Ao alterar um model em `app/models/`:

```bash
docker compose --profile test run --rm test alembic revision --autogenerate -m "descreva a alteração aqui"
```

Revise o arquivo gerado em `alembic/versions/` (o autogenerate nem sempre acerta tipos de coluna). Aplicar manualmente: `docker compose run --rm migrate`. Reverter a última: `docker compose --profile test run --rm test alembic downgrade -1`.

---

## 7. Populando dados iniciais (seed de permissões)

```bash
docker compose run --rm migrate python scripts/seed_permissions.py
```

Cria, de forma idempotente, todas as permissões definidas em `app/core/constants.py::PermissionCode` e uma role `admin` com todas elas atribuídas. Depois, atribua essa role a um usuário via `POST /users/{user_id}/roles`, ou marque `is_superuser=True` direto no banco para o primeiro administrador.

---

## 8. Qualidade de código

```bash
docker compose --profile test run --rm test ruff check .
docker compose --profile test run --rm test ruff check . --fix
docker compose --profile test run --rm test ruff format .
docker compose --profile test run --rm test mypy app
```

O CI (`.github/workflows/ci.yml`) roda exatamente esses comandos, mais a suíte de testes, a cada `push`/pull request.

### Checklist antes de commitar

```bash
docker compose --profile test run --rm test ruff check . --fix
docker compose --profile test run --rm test ruff format .
docker compose --profile test run --rm test ruff check .
docker compose --profile test run --rm test ruff format --check .
docker compose --profile test run --rm test mypy app
docker compose --profile test run --rm test
```

Pontos importantes:
- **A ordem importa** — rode `--fix`/`format` antes de `check`/`format --check`.
- **`--fix` não corrige tudo** — alguns avisos exigem edição manual (o `ruff` informa quantos "fixable" existem).
- **`format` e `check` são ferramentas diferentes** — uma cuida de estilo/espaçamento, a outra de imports/tipos/padrões. Rode as duas sempre.
- Se você editou `pyproject.toml` ou `Dockerfile`, adicione `--build` — sem isso, você testa contra uma imagem desatualizada.
- Se `mypy` reclamar de biblioteca sem stubs (`import-untyped`), prefira um `[[tool.mypy.overrides]]` no `pyproject.toml` em vez de instalar stubs de terceiros de qualidade incerta (já existe um exemplo lá, para `jose`/`passlib`).

---

## 9. Referência de variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `APP_NAME` | Não | `auth-service` | Nome da aplicação (aparece nos logs). |
| `APP_ENV` | Não | `development` | `development`, `staging`, `production` ou `test`. Em `production`, `/docs`/`/redoc`/`/openapi.json` ficam desativados. |
| `APP_DEBUG` | Não | `false` | Ativa logs mais verbosos. |
| `APP_HOST` / `APP_PORT` | Não | `0.0.0.0` / `8000` | Endereço em que o Uvicorn escuta. |
| `API_VERSION_PREFIX` | Não | `/api/v1` | Prefixo de todas as rotas versionadas. |
| `DATABASE_URL` | **Sim** | — | URL assíncrona do Postgres: `postgresql+asyncpg://usuario:senha@host:5432/banco`. |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` / `DATABASE_POOL_TIMEOUT_SECONDS` | Não | `10` / `20` / `30` | Tuning do pool de conexões. |
| `DATABASE_ECHO` | Não | `false` | Se `true`, loga todo SQL executado. |
| `REDIS_URL` | **Sim** | — | URL do Redis: `redis://host:6379/0`. |
| `JWT_SECRET_KEY` | **Sim** | — | Secret de assinatura dos tokens. Mín. 32 caracteres. |
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
| `MFA_ISSUER_NAME` | Não | `AuthService` | Nome exibido no app autenticador. |
| `SMTP_HOST` | Não | *(vazio)* | Se vazio, e-mails só são logados. |
| `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` / `SMTP_USE_TLS` | Não | ver `.env.example` | Configuração do servidor SMTP. |
| `CORS_ALLOWED_ORIGINS` | Não | `["http://localhost:3000"]` | Lista JSON de origens permitidas. |
| `LOG_LEVEL` | Não | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`. |
| `LOG_JSON` | Não | `true` | Se `false`, logs saem em texto legível. |

---

## 10. Solução de problemas comuns

**"A aplicação não inicia, erro de `ValidationError` no `Settings`"**
Alguma variável obrigatória (`DATABASE_URL`, `REDIS_URL` ou `JWT_SECRET_KEY`) está ausente ou inválida no `.env`.

**"`docker compose up` fica travado em `db` sem ficar saudável"**
A porta `5432` já pode estar em uso por outro Postgres na sua máquina. Pare o outro serviço ou mude o mapeamento de porta em `docker-compose.yml`.

**"Alterei o código mas a API não reflete a mudança"**
O serviço `app` roda com `--reload` e o código montado via volume — a maioria das mudanças reflete sozinha. Se alterou `pyproject.toml`, reconstrua: `docker compose up --build`.

**"Estou usando Podman e um serviço não sobe/sobe na hora errada"**
Veja [Opção C: Podman](#opção-c-podman) — `profiles:` e `depends_on: condition: service_healthy` têm suporte menos consistente no `podman-compose`.

**"A aplicação crasha na inicialização com erro de `bcrypt`/`passlib`"**
Incompatibilidade entre `passlib` e uma versão nova demais do `bcrypt` (4.1+). O `pyproject.toml` já trava `bcrypt<4.1` — se ainda ocorrer, force a reconstrução sem cache: `docker compose build --no-cache app migrate test`.

**"Recebo 401/403 em rotas que deveriam funcionar"**
Confira se o usuário tem `is_verified=True` e, para rotas administrativas, se ele tem a permissão RBAC necessária (`docs/permissions-reference.md`) ou `is_superuser=True`.

**"Alterei um model e o Alembic não detectou a mudança"**
Confirme que o model está importado em `alembic/env.py` — sem o import, o SQLAlchemy não sabe que a tabela existe.

---

## 11. Decisões de design ao longo do desenvolvimento

Registro de decisões tomadas durante a construção do projeto, para contexto de quem for mexer no código depois:

1. **`core/security.py` vs. pacote `security/`**: primitivas puras (passlib/jose/hashlib) ficam em `core/security.py`; a camada de domínio de segurança (`JWTHandler`, `PasswordHandler`, `MFAHandler`, `OAuth2Handler`) fica em `security/` — evita duplicar configuração criptográfica em dois lugares.
2. **Campos de MFA em `User`** (`mfa_enabled`/`mfa_secret`) adicionados junto com a implementação dos endpoints `/auth/mfa/*`.
3. **Schemas de `Session`** vivem em `auth_schema.py`, já que sessão nasce/morre como parte direta do ciclo de autenticação.
4. **`Role`/`Permission` usam exclusão física**; `User` usa exclusão lógica (`deleted_at`) — ver Seção 5 do `SPEC.md`.
5. **MFA (TOTP)** implementado só com a *standard library* (`hmac`, `base64`, `struct`), sem dependência extra.
6. **Claim `sid`** (session id) nos tokens, para que `/auth/logout` saiba qual sessão revogar sem exigir esse dado no corpo da requisição.
7. **Regra adicional**: um usuário não pode desativar/excluir a própria conta via `/users/{id}` — proteção contra se trancar fora do sistema.
8. **OAuth2** implementado como abstração genérica (Authorization Code Flow), sem provider concreto — não havia necessidade real de um provider específico ainda quando essa camada foi construída.
9. **`Dockerfile` na raiz do projeto**, não em `docker/Dockerfile` — o `podman-compose` (testado na versão 1.6.0, no Windows) não resolve corretamente o campo `dockerfile:` apontando para uma subpasta. Manter na raiz funciona igual em Docker e Podman, sem precisar declarar o campo no `docker-compose.yml`.
10. **`bcrypt` travado em `4.0.x`**: `passlib` (sem atualizações desde 2020) quebra com `bcrypt` 4.1+, que removeu um atributo interno usado pela detecção de versão do passlib. Travar a versão resolve sem trocar de biblioteca.
