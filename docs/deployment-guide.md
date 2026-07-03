# Guia de Deploy — subindo o Auth Service em produção

Este documento explica como colocar o Auth Service (aplicação + PostgreSQL + Redis) no ar em produção. Ele parte do que já existe no projeto (`Dockerfile`, `docker-compose.yml`, `alembic/`) e explica o que muda entre "ambiente de desenvolvimento" e "produção de verdade".

---

## Sumário

- [1. O que muda entre dev e produção](#1-o-que-muda-entre-dev-e-produção)
- [2. Preparando os segredos de produção](#2-preparando-os-segredos-de-produção)
- [3. Banco de dados (PostgreSQL) em produção](#3-banco-de-dados-postgresql-em-produção)
- [4. Redis em produção](#4-redis-em-produção)
- [5. A aplicação (FastAPI)](#5-a-aplicação-fastapi)
- [6. Migrações no fluxo de deploy](#6-migrações-no-fluxo-de-deploy)
- [7. Opção A — VPS único com Docker Compose](#7-opção-a--vps-único-com-docker-compose)
- [8. Opção B — Plataforma de containers (PaaS)](#8-opção-b--plataforma-de-containers-paas)
- [9. Reverse proxy e HTTPS](#9-reverse-proxy-e-https)
- [10. Observabilidade](#10-observabilidade)
- [11. Checklist de segurança antes de lançar](#11-checklist-de-segurança-antes-de-lançar)
- [12. Checklist de cada deploy](#12-checklist-de-cada-deploy)

---

## 1. O que muda entre dev e produção

O `docker-compose.yml` do repositório foi feito para **desenvolvimento local** — ele monta o código-fonte como volume (`--reload`), sobe um Postgres/Redis descartáveis no mesmo host, e inclui um serviço `test` que não faz sentido em produção. Em produção:

| Aspecto | Desenvolvimento (`docker-compose.yml`) | Produção |
|---|---|---|
| Código da aplicação | Montado via volume, `--reload` | Copiado *dentro* da imagem no build (já é assim no `Dockerfile`) — sem volume, sem reload |
| Banco de dados | Container Postgres descartável, sem backup | Serviço gerenciado (recomendado) ou container com volume persistente + backup |
| Redis | Container descartável | Serviço gerenciado ou container com restart automático (dados de rate limit são aceitáveis de perder num restart) |
| Segredos | `.env` local, versionado como exemplo | Variáveis de ambiente injetadas pela plataforma/secret manager, **nunca** um arquivo `.env` commitado |
| `APP_ENV` | `development` | `production` (desativa `/docs`, `/redoc`, `/openapi.json`) |
| HTTPS | Não necessário | Obrigatório |
| Réplicas da app | 1 container | 2+ containers atrás de um load balancer (a app é *stateless* — todo estado fica no Postgres/Redis, então escalar horizontalmente é direto) |

---

## 2. Preparando os segredos de produção

Nunca reutilize os valores do `.env` de desenvolvimento em produção. Gere segredos novos:

```bash
# JWT_SECRET_KEY — novo, único para produção
openssl rand -hex 32
```

Checklist de variáveis que **precisam** de um valor real de produção (ver a referência completa no README, seção 10):

- `JWT_SECRET_KEY` — gerado acima, guardado num secret manager (não em texto puro em disco do servidor).
- `DATABASE_URL` — apontando para o Postgres de produção (seção 3).
- `REDIS_URL` — apontando para o Redis de produção (seção 4).
- `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM_EMAIL` — um provedor de e-mail transacional real (SendGrid, SES, Postmark, etc.) — sem isso, confirmação de cadastro e reset de senha não chegam a lugar nenhum.
- `CORS_ALLOWED_ORIGINS` — só os domínios reais do(s) seu(s) frontend(s), nunca `*` nem `localhost`.
- `APP_ENV=production`.

**Onde guardar isso:** use o gerenciador de secrets da sua plataforma (AWS Secrets Manager, GCP Secret Manager, variáveis de ambiente do Railway/Render/Fly.io, Docker Swarm secrets, etc.). Se o deploy for manual num VPS, ao menos mantenha o arquivo de env fora do diretório do Git, com permissão de leitura restrita:

```bash
sudo mkdir -p /etc/auth-service
sudo chmod 700 /etc/auth-service
sudo nano /etc/auth-service/.env   # cole as variáveis de produção aqui
sudo chmod 600 /etc/auth-service/.env
```

---

## 3. Banco de dados (PostgreSQL) em produção

### Opção recomendada: Postgres gerenciado

Serviços como **Amazon RDS**, **Google Cloud SQL**, **Supabase**, **Neon** ou **Railway/Render Postgres add-on** cuidam de backup automático, failover e patches de segurança — isso tira de você a responsabilidade mais arriscada de operar um banco de produção manualmente. Recomendado para a maioria dos casos.

Passos gerais (variam por provedor):
1. Provisione uma instância Postgres **17** (versão exigida pela Seção 2 do projeto).
2. Crie um banco de dados e um usuário dedicado (não use o usuário `postgres` root da instância).
3. Anote a connection string e monte a `DATABASE_URL` no formato assíncrono:
   ```
   postgresql+asyncpg://usuario:senha@host:5432/nome_do_banco
   ```
   Repare no `+asyncpg` — é obrigatório (o projeto usa SQLAlchemy assíncrono).
4. Se o provedor exigir SSL (a maioria exige em produção), adicione o parâmetro:
   ```
   postgresql+asyncpg://usuario:senha@host:5432/banco?ssl=require
   ```

### Alternativa: Postgres self-hosted em container

Se você optar por rodar o próprio Postgres (ex: VPS único, seção 7), use volume persistente e configure backup:

```yaml
db:
  image: postgres:17-alpine
  restart: always
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
  volumes:
    - auth_service_postgres_data:/var/lib/postgresql/data
  # Em produção, NÃO exponha a porta 5432 publicamente — remova o
  # mapeamento "ports:" a menos que precise acessar de fora do host.
```

**Backup mínimo viável** (cron diário rodando `pg_dump` fora do container, para um storage externo):

```bash
#!/bin/bash
# /etc/cron.daily/backup-auth-service-db
docker exec auth-service-db-1 pg_dump -U auth_service auth_service \
  | gzip > /backups/auth-service-$(date +%F).sql.gz

# Mantenha só os últimos 30 dias
find /backups -name "auth-service-*.sql.gz" -mtime +30 -delete
```

Envie esses backups para um storage fora do próprio servidor (S3, Backblaze B2, etc.) — um backup que mora no mesmo disco do banco não protege contra falha de disco/servidor.

---

## 4. Redis em produção

O Redis aqui só é usado para **contadores de rate limiting** (`RateLimitMiddleware`) — não guarda dados de negócio, sessões, nem nada que precise sobreviver a um restart. Isso simplifica a operação:

- **Perda de dados do Redis em um restart é aceitável** — na pior hipótese, os contadores de rate limit zeram, o que só significa que alguém tem uma nova janela de tentativas, não uma falha de segurança grave.
- Ainda assim, prefira um Redis gerenciado (**Upstash**, **Redis Cloud**, **AWS ElastiCache**) se já estiver usando um provedor de nuvem — evita mais um componente para você mesmo operar.
- Se for self-hosted, `restart: always` no container já é suficiente — não é necessário volume persistente para este caso de uso específico do projeto.

```yaml
redis:
  image: redis:7-alpine
  restart: always
  # Sem "ports:" expostas publicamente — só a rede interna entre
  # app e redis precisa alcançar essa porta.
```

---

## 5. A aplicação (FastAPI)

### Build da imagem

O `Dockerfile` já é multi-stage e o stage `runtime` (usado por padrão) já é mínimo — sem ferramentas de build ou teste. Para produção, construa e publique a imagem num registro de containers:

```bash
docker build -t seu-registro/auth-service:1.0.0 .
docker push seu-registro/auth-service:1.0.0
```

Use uma tag de versão real (`1.0.0`, ou o hash do commit) — nunca só `latest` em produção, para que rollback seja possível apontando para uma tag anterior.

### Múltiplas réplicas

A aplicação é **stateless**: todo estado (usuários, sessões, tokens revogados) vive no Postgres; rate limiting vive no Redis. Isso significa que rodar **múltiplos containers da aplicação atrás de um load balancer** é seguro e é a forma recomendada de escalar — não há necessidade de "sticky sessions".

### Health check

O endpoint `GET /api/v1/health` (não exige autenticação, não toca banco/Redis) já existe para isso — configure seu orquestrador/load balancer para usá-lo:

- **Docker/Podman Compose**: o `HEALTHCHECK` já está no `Dockerfile`.
- **Kubernetes**: use como `livenessProbe`/`readinessProbe`.
- **Load balancer de nuvem** (ALB, Cloud Load Balancing, etc.): configure o *health check path* para `/api/v1/health`.

### Variáveis de ambiente

Nunca reconstrua a imagem para mudar configuração — todas as variáveis (Seção 10 do README) são lidas em tempo de execução. Configure-as via:
- Variáveis de ambiente do orquestrador/PaaS, **ou**
- Um arquivo de env fora do controle de versão (`/etc/auth-service/.env`, ver seção 2).

---

## 6. Migrações no fluxo de deploy

**Nunca** deixe a aplicação rodar `alembic upgrade head` automaticamente a cada início do container em produção (diferente do `docker-compose.yml` de desenvolvimento, que faz isso por conveniência). Em produção, migrações devem ser um passo **explícito e único**, executado antes de trocar o tráfego para a nova versão:

```bash
# Rode a migração uma vez, contra o banco de produção, antes do deploy da nova versão da app
docker run --rm --env-file /etc/auth-service/.env seu-registro/auth-service:1.0.0 \
  alembic upgrade head
```

Por quê isso importa: se você tiver **múltiplas réplicas** subindo ao mesmo tempo (rolling deploy) e cada uma tentar rodar a migração automaticamente, você corre risco de condição de corrida no schema. Rodar como um passo único e separado evita isso.

**Migrações que quebram compatibilidade** (ex: remover uma coluna que a versão antiga da app ainda lê) exigem cuidado extra num deploy com múltiplas réplicas rodando versões diferentes simultaneamente (rolling deploy) — prefira sempre que possível dividir em duas migrações/deploys: primeiro tornar a coluna opcional/adicionar a nova, depois (num deploy seguinte, quando todas as réplicas já estiverem na versão nova) remover a antiga.

---

## 7. Opção A — VPS único com Docker Compose

Para escala pequena/média, um único servidor (VPS) com Docker/Podman Compose é suficiente. Diferenças em relação ao `docker-compose.yml` de desenvolvimento:

```yaml
# docker-compose.prod.yml (crie este arquivo separado — não substitua o de dev)
services:
  db:
    image: postgres:17-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - auth_service_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10

  app:
    image: seu-registro/auth-service:1.0.0   # imagem já publicada — sem "build:"
    restart: always
    env_file:
      - /etc/auth-service/.env
    ports:
      - "8000:8000"   # ou apenas exposto internamente, se o reverse proxy estiver no mesmo host
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    # Sem "volumes:" de código-fonte, sem "--reload" — a imagem já
    # tem tudo que precisa, construída uma vez no CI/CD.

volumes:
  auth_service_postgres_data:
```

Note as diferenças-chave em relação ao arquivo de desenvolvimento:
- `app` usa `image:` (uma imagem já publicada), não `build:` — a imagem é construída uma vez no seu pipeline de CI/CD, não no servidor de produção.
- Nenhum volume monta código-fonte.
- Nenhum serviço `test`.
- `restart: always` em tudo (em vez de `unless-stopped`), para recuperação automática após reinício do host.
- Migração roda separadamente (seção 6), não como serviço `migrate` automático no `up`.

Subindo:

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 8. Opção B — Plataforma de containers (PaaS)

Se preferir não gerenciar servidores diretamente, plataformas como **Railway**, **Render**, **Fly.io** ou **AWS App Runner** constroem e rodam a imagem a partir do `Dockerfile` do repositório. Passos gerais (a interface exata varia por plataforma):

1. Conecte o repositório Git à plataforma.
2. A plataforma detecta o `Dockerfile` na raiz automaticamente.
3. Provisione os add-ons de **PostgreSQL** e **Redis** oferecidos pela própria plataforma (mais simples que configurar externamente).
4. Configure as variáveis de ambiente (seção 2) no painel da plataforma — a maioria já injeta `DATABASE_URL`/`REDIS_URL` automaticamente quando você usa os add-ons deles (confira o formato: precisa ter `+asyncpg` no caso do Postgres, o que pode exigir ajustar a URL fornecida).
5. Configure o *health check path* para `/api/v1/health`.
6. Configure um passo de deploy (*release command*, ou equivalente) para rodar `alembic upgrade head` antes de cada deploy — a maioria dessas plataformas tem esse conceito nativamente.

---

## 9. Reverse proxy e HTTPS

A aplicação em si serve HTTP puro na porta 8000 — **HTTPS é responsabilidade da camada na frente dela**:

- **PaaS** (Railway, Render, Fly.io): HTTPS já vem configurado automaticamente, nada a fazer.
- **VPS próprio**: coloque um reverse proxy na frente — **Caddy** é a opção mais simples (certificado TLS automático via Let's Encrypt, renovação automática):

```caddyfile
# /etc/caddy/Caddyfile
auth.suaempresa.com {
    reverse_proxy localhost:8000
}
```

Alternativas equivalentes: Nginx + Certbot, ou Traefik (mais configuração, mais controle).

**Nunca** exponha a aplicação diretamente na internet sem TLS — tokens JWT trafegando em texto puro por HTTP são interceptáveis.

---

## 10. Observabilidade

- **Logs**: já saem em JSON estruturado (`LOG_JSON=true`, padrão) — direcione o `stdout` dos containers para seu agregador de logs (CloudWatch Logs, Grafana Loki, Datadog, etc.). Cada log já inclui `correlation_id` (via header `X-Request-ID`), permitindo rastrear todas as etapas de uma única requisição.
- **Métricas**: o projeto não expõe um endpoint `/metrics` (Prometheus) nativamente — se precisar, é uma extensão razoável de se adicionar depois (`prometheus-fastapi-instrumentator` é uma opção comum no ecossistema FastAPI), fora do escopo deste projeto até que haja essa necessidade real.
- **Alertas mínimos recomendados**: falha no health check por mais de N minutos, taxa de erros 5xx acima do normal, uso de disco do Postgres acima de 80%.

---

## 11. Checklist de segurança antes de lançar

- [ ] `APP_ENV=production` (desativa `/docs`, `/redoc`, `/openapi.json` publicamente).
- [ ] `JWT_SECRET_KEY` gerado especificamente para produção, nunca reaproveitado do `.env.example` ou de desenvolvimento.
- [ ] `CORS_ALLOWED_ORIGINS` restrito aos domínios reais do frontend — nunca `*`.
- [ ] HTTPS obrigatório (seção 9) — sem exceção, nem "por enquanto".
- [ ] Porta do Postgres/Redis **não exposta publicamente** — só acessível pela rede interna entre os containers/serviços da aplicação.
- [ ] Backup do Postgres configurado e **testado** (restaurar um backup pelo menos uma vez, para confirmar que funciona).
- [ ] SMTP configurado com um provedor real — confirmação de e-mail e reset de senha são fluxos críticos de segurança, não podem depender de "configurar depois".
- [ ] `.env` de produção nunca commitado no Git, em nenhum branch, em nenhum momento do histórico.
- [ ] Rodar `scripts/seed_permissions.py` contra o banco de produção antes do primeiro uso real, e atribuir a role `admin` (ou `is_superuser=True`) a pelo menos um usuário administrador.

---

## 12. Checklist de cada deploy

- [ ] Build da imagem com uma tag de versão específica (não `latest`).
- [ ] Rodar `alembic upgrade head` contra o banco de produção **antes** de trocar o tráfego para a nova versão.
- [ ] Confirmar que o health check (`/api/v1/health`) responde `200` na nova versão antes de desviar tráfego para ela (se o processo de deploy não fizer isso automaticamente).
- [ ] Monitorar logs/taxa de erro nos minutos seguintes ao deploy.
- [ ] Ter um plano de rollback claro: apontar de volta para a tag de imagem anterior é suficiente, **a menos que** a migração desse deploy tenha removido algo que a versão anterior ainda precisa (ver nota sobre migrações compatíveis na seção 6).
