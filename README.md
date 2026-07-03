# Auth Service

Microsserviço de **autenticação e autorização**, pronto para produção, construído em **FastAPI + PostgreSQL + SQLAlchemy 2.x (async)**. Ele centraliza login, gestão de sessões, RBAC (roles/permissões) e MFA (TOTP), para que qualquer sistema cliente delegue essas responsabilidades via API em vez de reimplementá-las internamente.

Este README foi escrito para que qualquer pessoa — de quem nunca rodou um projeto FastAPI a quem já mantém sistemas em produção — consiga clonar, configurar e rodar o projeto do zero.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
  - [Usando Podman em vez de Docker](#usando-podman-em-vez-de-docker)
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
- [9. Estrutura de pastas](#9-estrutura-de-pastas)
- [10. Referência de variáveis de ambiente](#10-referência-de-variáveis-de-ambiente)
- [11. Solução de problemas comuns](#11-solução-de-problemas-comuns)
- [12. Contribuindo](#12-contribuindo)
- [13. Decisões de implementação](#13-decisões-de-implementação)

---

## Pré-requisitos

Este projeto roda **exclusivamente em containers** — não há suporte a instalação local do Python/PostgreSQL/Redis. Isso garante que o ambiente de qualquer pessoa (independente de sistema operacional ou versões instaladas) seja idêntico ao de produção.

Você precisa de **um** destes dois conjuntos de ferramentas:

| Opção A: Docker (mais comum) | Opção B: Podman (mais leve, sem Docker Desktop) |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) 24+ | [Podman](https://podman.io/docs/installation) 5+ |
| Docker Compose (já incluso no Docker Desktop) | `podman-compose` (`pip install podman-compose`) |

Nada de Python, PostgreSQL ou Redis precisa estar instalado na sua máquina — mesmo para rodar os scripts de seed, que também executam dentro de um container.

Para contribuir com código, também é útil ter o [Git](https://git-scm.com/downloads) instalado.

> Todos os comandos deste README usam `docker compose`. Se você está usando **Podman**, veja a seção abaixo antes de continuar — a substituição é simples, mas tem duas particularidades que vale saber de antemão.

### Usando Podman em vez de Docker

O Podman não tem o subcomando `compose` nativo funcional sem um provedor externo — por isso usamos o `podman-compose` (pacote Python), testado e confirmado funcionando neste projeto.

**Configuração (uma vez só):**

```powershell
# 1. Crie e inicie a máquina do Podman (Windows/macOS; não é necessário no Linux nativo)
podman machine init
podman machine start

# 2. Instale o podman-compose
pip install podman-compose
```

**Uso no dia a dia:** troque `docker compose` por `podman-compose` (sem espaço, com hífen) em **todo comando deste README**. Exemplos:

| Este README diz | Com Podman, rode |
|---|---|
| `docker compose up --build` | `podman-compose up --build` |
| `docker compose up -d` | `podman-compose up -d` |
| `docker compose logs -f app` | `podman-compose logs -f app` |
| `docker compose down` / `down -v` | `podman-compose down` / `down -v` |
| `docker compose run --rm migrate` | `podman-compose run --rm migrate` |
| `docker compose --profile test run --rm test <comando>` | `podman-compose run --rm test <comando>` |

**Duas particularidades do `podman-compose` (versão 1.6.0, a testada) para ficar de olho:**

1. **`profiles:` pode não ser respeitado** — o serviço `test` usa `profiles: [test]` justamente para não subir junto no `up` normal. Se ele subir mesmo assim ao rodar `podman-compose up --build`, pare-o manualmente (`podman-compose stop test`) ou suba só os serviços que quer, nomeando-os: `podman-compose up --build db redis migrate app`.
2. **`depends_on: condition: service_healthy` pode ser menos confiável** que no Docker Compose — se `migrate`/`app` tentar subir antes do Postgres/Redis estarem realmente prontos, suba o banco primeiro e aguarde alguns segundos antes do resto:
   ```powershell
   podman-compose up -d db redis
   # aguarde alguns segundos
   podman-compose up --build migrate app
   ```

Se encontrar qualquer outro comportamento diferente do documentado, é provável que seja uma particularidade de versão do `podman-compose` — abra uma *issue* descrevendo o erro (seção 12).

### Configurando autocomplete no editor (opcional)

Como o projeto roda inteiramente em container, seu sistema operacional não tem `fastapi`, `sqlalchemy` e as demais dependências instaladas — então seu editor (VS Code, PyCharm, etc.) provavelmente vai mostrar avisos do tipo `Import "fastapi" could not be resolved`. **Isso não afeta a aplicação rodando** — é só o editor não tendo onde procurar as bibliotecas para autocomplete/checagem de tipos.

Se quiser eliminar esses avisos e ter autocomplete completo, crie um ambiente virtual **só para o editor usar como referência** — ele nunca roda a aplicação nem se conecta a nada, é puramente para o Pylance/IntelliSense conseguirem ler as bibliotecas:

```bash
python -m venv .venv-editor
```

Ative o ambiente:

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

No VS Code: `Ctrl+Shift+P` (ou `Cmd+Shift+P` no Mac) → **Python: Select Interpreter** → escolha o interpretador dentro de `.venv-editor`. Em outras IDEs, o equivalente é configurar o interpretador Python do projeto para apontar pra esse mesmo caminho.

Esse passo é **totalmente opcional** — pular ele não impede a aplicação de rodar, só deixa o editor sem autocomplete. E ele não usa recursos do seu notebook além do espaço em disco (~300–400MB): não é um processo, só arquivos parados, diferente da VM do Docker/Podman (essa sim consome CPU/RAM o tempo em que estiver "Running").

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

2. **`DATABASE_URL`** e **`REDIS_URL`** — os valores padrão do `.env.example` já apontam para os nomes dos serviços do `docker-compose.yml` (`db` e `redis`). Não altere isso — esses nomes só resolvem dentro da rede interna criada pelo Docker Compose, e é assim que a aplicação sempre roda neste projeto.

3. **`SMTP_HOST`** — pode deixar em branco em ambiente de desenvolvimento. Sem SMTP configurado, o serviço apenas registra em log os e-mails que enviaria (confirmação de cadastro, reset de senha), em vez de falhar.

Todas as outras variáveis têm valores padrão razoáveis para desenvolvimento — a lista completa e o que cada uma faz está na [seção 10](#10-referência-de-variáveis-de-ambiente).

---

## 3. Rodando a aplicação

Com o `.env` configurado (passo anterior), suba tudo com um comando:

```bash
docker compose up --build
```

Isso vai, em ordem:
1. Construir a imagem da aplicação (`Dockerfile`, multi-stage).
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

### Quando preciso reconstruir a imagem (`--build`)?

Os serviços `app`, `migrate` e `test` montam `app/`, `alembic/` e `scripts/` do seu computador direto dentro do container (`volumes:` no `docker-compose.yml`) — e `test` também monta `tests/`. Isso significa que, para a maior parte do trabalho do dia a dia, **editar esses arquivos e salvar já é suficiente**: o `app` roda com `--reload` (recarrega sozinho a cada mudança), e `migrate`/`test` sempre leem a versão mais recente do arquivo na hora que você os executa.

| Você alterou... | Precisa de `--build`? |
|---|---|
| Qualquer arquivo em `app/` | **Não** — `--reload` recarrega sozinho |
| Qualquer arquivo em `tests/` | **Não** — lido na hora pelo serviço `test` |
| Qualquer arquivo em `alembic/` (incluindo novas migrations) | **Não** |
| Qualquer arquivo em `scripts/` | **Não** |
| `pyproject.toml` (adicionar/remover dependência) | **Sim** — a dependência só existe dentro da imagem construída |
| `Dockerfile` | **Sim** |
| `docker-compose.yml` | Depende: mudanças em `volumes`/`command`/`ports`/`environment` pedem só `docker compose up` de novo (sem `--build`); mudanças que afetam o *build* (ex: `target:`) pedem `--build` |
| `.env` | **Não** — lido em tempo de execução, não durante o build; basta reiniciar o container (`docker compose restart app`, ou `Ctrl+C` e subir de novo) |

Na dúvida, `docker compose up --build` sempre funciona (o Docker reaproveita as camadas de cache que não mudaram, então não é lento na maioria das vezes) — os casos "Não" acima são só para evitar esperar um build sem necessidade.

---

## 4. Verificando que está funcionando

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

## 5. Rodando os testes

Os testes de integração e de API rodam contra um **banco de dados real** (não um mock). Um serviço dedicado do Docker Compose (`test`) já vem com `pytest`, `ruff` e `mypy` instalados — ele usa o [profile](https://docs.docker.com/compose/how-tos/profiles/) `test`, então não sobe junto com `docker compose up` normal.

```bash
# Suba db/redis se ainda não estiverem no ar:
docker compose up -d db redis

# Rode a suíte completa:
docker compose --profile test run --rm test
```

Com relatório de cobertura (já é o padrão do comando acima, mas para customizar):

```bash
docker compose --profile test run --rm test pytest --cov=app --cov-report=term-missing
```

Rodando só uma camada de teste:

```bash
docker compose --profile test run --rm test pytest tests/unit/            # unitários (services/security, com mocks)
docker compose --profile test run --rm test pytest tests/integration/     # repositórios, contra banco real
docker compose --profile test run --rm test pytest tests/api/             # fluxos HTTP completos
```

> Os testes criam e destroem as tabelas automaticamente a cada execução (`tests/conftest.py`) — não aponte `DATABASE_URL` para o banco de **produção** ao rodar testes.

### Salvando a saída dos testes em arquivo

A suíte completa gera bastante texto — se houver várias falhas, rola pra fora do buffer do terminal e fica difícil de revisar (ou de colar em algum lugar pra pedir ajuda). Salve em um arquivo **e** continue vendo em tempo real na tela, com o mesmo comando:

```powershell
# Windows (PowerShell)
docker compose --profile test run --rm test 2>&1 | Tee-Object -FilePath pytest_output.txt
```
```bash
# Linux / macOS
docker compose --profile test run --rm test 2>&1 | tee pytest_output.txt
```

O que cada parte faz:
- `2>&1` — junta a saída de erro (`stderr`) com a saída padrão (`stdout`) num único fluxo, para nada se perder (alguns avisos do Podman/Docker saem por `stderr`).
- `Tee-Object -FilePath pytest_output.txt` (PowerShell) / `tee pytest_output.txt` (bash) — o "Tee" mostra a saída na tela **e** grava em `pytest_output.txt` ao mesmo tempo, sem precisar escolher um ou outro.

Isso cria `pytest_output.txt` na raiz do projeto. Para conferir só o final (geralmente onde está o resumo `X passed, Y failed`), sem reabrir o arquivo inteiro:

```powershell
Get-Content pytest_output.txt -Tail 30
```
```bash
tail -n 30 pytest_output.txt
```

> **Atenção (Windows/PowerShell):** o `Tee-Object` grava o arquivo em UTF-16 por padrão. Se for abrir `pytest_output.txt` em outra ferramenta que espere UTF-8, pode ser necessário converter a codificação antes.

---

## 6. Migrações de banco de dados (Alembic)

A primeira migração (`alembic/versions/0001_initial_schema.py`) já cria todo o schema e roda automaticamente ao subir o projeto (serviço `migrate`). Ao alterar um model em `app/models/`, gere uma nova migração usando o serviço `test` (que tem o código-fonte completo e as dependências necessárias):

```bash
docker compose --profile test run --rm test alembic revision --autogenerate -m "descreva a alteração aqui"
```

Revise o arquivo gerado em `alembic/versions/` (o autogenerate nem sempre acerta 100%, especialmente em alterações de tipo de coluna). A nova migração roda automaticamente na próxima vez que você subir o projeto (`docker compose up`), ou manualmente:

```bash
docker compose run --rm migrate
```

Para reverter a última migração:

```bash
docker compose --profile test run --rm test alembic downgrade -1
```

---

## 7. Populando dados iniciais (seed de permissões)

Um RBAC não é útil sem permissões e uma role de administrador cadastradas. Rode o script de seed uma vez, após a primeira migração:

```bash
docker compose run --rm migrate python scripts/seed_permissions.py
```

Isso cria, de forma idempotente (pode rodar de novo sem duplicar), todas as permissões definidas em `app/core/constants.py::PermissionCode` e uma role `admin` com todas elas atribuídas. Depois, atribua a role `admin` a um usuário seu via `POST /api/v1/users/{user_id}/roles`, ou marque `is_superuser=True` diretamente no banco para o primeiro usuário (bypassa RBAC completamente).

---

## 8. Qualidade de código

```bash
docker compose --profile test run --rm test ruff check .            # lint
docker compose --profile test run --rm test ruff check . --fix      # lint com correção automática do que for seguro
docker compose --profile test run --rm test ruff format .           # formatação
docker compose --profile test run --rm test mypy app                # checagem de tipos estática (modo strict)
```

O pipeline de CI (`.github/workflows/ci.yml`) roda exatamente esses comandos, mais a suíte de testes, a cada `push`/`pull request`.

---

## 9. Estrutura de pastas

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
├── docs/                          # documentação estendida do projeto (ver docs/README.md)
├── scripts/                       # scripts utilitários de operação (ver scripts/README.md)
│
├── .env.example                   # modelo de variáveis de ambiente (sem segredos reais)
├── .gitignore
├── Dockerfile                      # build multi-stage (builder / test / runtime)
├── docker-compose.yml              # orquestra app + PostgreSQL + Redis para desenvolvimento
├── pyproject.toml                  # dependências, config do Ruff/Mypy/Pytest
└── README.md                       # este arquivo
```

**Por onde começar a ler o código**, se você é novo no projeto: `app/services/` primeiro (é onde a lógica de negócio vive), depois `app/api/routes/` para ver como cada endpoint usa os services, e só depois `app/repositories/`/`app/models/` para entender a persistência.

### Sobre as pastas docs/ e scripts/

Essas duas pastas fazem parte da estrutura do projeto (para acomodar crescimento futuro), mas propositalmente não vêm cheias de conteúdo especulativo:

- **`docs/`** — reservada para documentação estendida que não cabe num README (diagramas de arquitetura, ADRs — *Architecture Decision Records* —, coleções do Postman/Insomnia, runbooks de incidente). Veja `docs/README.md` para o que colocar aqui conforme o projeto crescer.
- **`scripts/`** — reservada para scripts operacionais de manutenção, rodados manualmente ou via cron/job agendado (fora do ciclo de requisição HTTP). Já vem com `scripts/seed_permissions.py` funcional (seção 7) — veja `scripts/README.md` para a lista completa e convenções para adicionar novos scripts.

---

## 10. Referência de variáveis de ambiente

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
| `LOG_JSON` | Não | `true` | Se `false`, logs saem em texto legível em vez de JSON (útil ao observar `docker compose logs -f app` interativamente). |

---

## 11. Solução de problemas comuns

**"A aplicação não inicia, erro de ValidationError no Settings"**
Alguma variável obrigatória (`DATABASE_URL`, `REDIS_URL` ou `JWT_SECRET_KEY`) está ausente ou inválida no `.env`. Revise a seção 2.

**"docker compose up fica travado em db sem ficar saudável"**
A porta `5432` já pode estar em uso por outro Postgres na sua máquina. Pare o outro serviço ou mude o mapeamento de porta em `docker-compose.yml`.

**"Alterei o código mas a API não reflete a mudança"**
O serviço `app` já roda com `--reload` e o código montado via volume (`docker-compose.yml`), então a maioria das alterações em `app/` é refletida automaticamente. Se você alterou `pyproject.toml` (novas dependências), é preciso reconstruir a imagem: `docker compose up --build`.

**"Estou usando Podman e um serviço não sobe/sobe na hora errada"**
Veja a seção [Usando Podman em vez de Docker](#usando-podman-em-vez-de-docker) — `profiles:` e `depends_on: condition: service_healthy` têm suporte menos consistente no `podman-compose` do que no Docker Compose.

**"A aplicação crasha na inicialização com `AttributeError: module 'bcrypt' has no attribute '__about__'` ou `ValueError: password cannot be longer than 72 bytes`"**
Incompatibilidade entre `passlib` e uma versão nova demais do `bcrypt` (4.1+). O `pyproject.toml` já trava `bcrypt<4.1` — se você ainda vir esse erro, a imagem foi construída antes dessa correção (ou o cache do build ainda tem a versão antiga). Force a reconstrução:
```bash
docker compose build --no-cache app migrate test
docker compose up
```

**"Recebo 401/403 em rotas que deveriam funcionar"**
Confira se o usuário está com `is_verified=True` (login exige confirmação de e-mail) e, para rotas administrativas, se ele tem a permissão RBAC necessária (seção 7) ou `is_superuser=True`.

**"Alterei um model e o Alembic não detectou a mudança"**
Confirme que o novo model está importado em `alembic/env.py` — sem o import, o SQLAlchemy não sabe que a tabela existe.

---

## 12. Contribuindo

Contribuições são bem-vindas. Fluxo sugerido:

1. Abra uma *issue* descrevendo o problema/melhoria antes de codar, para alinhar escopo.
2. Crie um branch a partir de `main`: `git checkout -b minha-feature`.
3. Rode `docker compose --profile test run --rm test ruff check .`, `... ruff format .` e `... mypy app` antes de commitar — o CI vai rejeitar o PR se algum falhar (seção 8).
4. Adicione/atualize testes para qualquer mudança de comportamento — `docker compose --profile test run --rm test` precisa passar (seção 5).
5. Abra o Pull Request descrevendo o que mudou e por quê.

---

## 13. Decisões de implementação

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
12. **`Dockerfile` na raiz do projeto, não em `docker/Dockerfile`**: a especificação original pedia a segunda estrutura, mas `podman-compose` (testado na versão 1.6.0, no Windows) não resolve corretamente o campo `dockerfile:` apontando para uma subpasta — falha com "no Containerfile or Dockerfile specified or found", mesmo com o contexto de build correto. Mover o `Dockerfile` para a raiz (convenção padrão, sem precisar declarar `dockerfile:` no `docker-compose.yml`) resolve o problema de forma compatível tanto com Docker quanto com Podman.
13. **`bcrypt` travado em `4.0.x`** (`pyproject.toml`): `passlib` 1.7.4 (sem atualizações desde 2020) quebra a inicialização da aplicação com `bcrypt` 4.1+ — a lib removeu um atributo interno (`__about__.__version__`) usado pelo passlib para detectar a versão do backend, e o caminho de fallback do passlib então esbarra na checagem mais rígida do bcrypt 4.1+ para senhas acima de 72 bytes, levantando `ValueError` (`password cannot be longer than 72 bytes`) mesmo para senhas curtas, ainda na importação dos módulos. Travar `bcrypt<4.1` resolve sem trocar de biblioteca.