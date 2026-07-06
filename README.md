# Auth Service

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)
![Redis](https://img.shields.io/badge/Redis-7-red)
![License](https://img.shields.io/badge/Licença-MIT-orange)
![Tests](https://img.shields.io/badge/Tests-74_passing-success)

> Microsserviço de autenticação e autorização construído com FastAPI, feito para ser plugado em qualquer sistema sem reescrever a camada de identidade.

---

## 📖 Visão geral

O **Auth Service** é um microsserviço independente que resolve autenticação, autorização e gerenciamento de usuários de forma centralizada. Em vez de reimplementar login, controle de acesso e gestão de identidade em cada novo projeto, este serviço assume essa responsabilidade por completo — deixando as outras aplicações livres para focar só nas próprias regras de negócio.

Funciona tanto como um serviço de autenticação pronto pra produção quanto como base para novos projetos que precisem de uma fundação de identidade sólida desde o primeiro dia.

Mais do que uma API de login, é uma plataforma completa de autenticação e autorização, pronta para servir como base de aplicações ou como template para acelerar o início de novos sistemas sem abrir mão de segurança, escalabilidade ou boas práticas.

---

## ✨ Funcionalidades

**Autenticação**
- Cadastro, confirmação de e-mail e login
- Access token + refresh token (JWT), com rotação automática e detecção de reuso (proteção contra replay)
- Recuperação e alteração de senha
- Autenticação multifator (TOTP)
- Logout individual ou em todos os dispositivos, com gerenciamento de sessões por dispositivo

**Autorização**
- RBAC completo: usuários, roles e permissões granulares (`recurso:acao`)
- Verificação de permissão via dependência do FastAPI, sem repetição de código nas rotas

**Segurança**
- Hash de senha com bcrypt/argon2, nunca em texto puro
- Refresh tokens armazenados só como hash
- Rate limiting por IP e bloqueio de conta após tentativas de login falhas
- Headers de segurança e logs de auditoria estruturados em todas as rotas sensíveis

**Administração**
- CRUD completo de usuários, roles e permissões
- Ativação, desativação e exclusão lógica de contas

---

## ❓ Por que um microsserviço de autenticação?

Conforme uma aplicação cresce, manter autenticação acoplada ao sistema principal vira um ponto de fricção — toda nova aplicação do mesmo ecossistema acaba reimplementando login, hashing de senha e RBAC do zero. Separar essa responsabilidade em um serviço dedicado traz:

- Reutilização entre múltiplos projetos, sem duplicar lógica de identidade
- Um único lugar para auditar segurança de autenticação
- Padronização do contrato de autenticação para qualquer cliente (web, mobile, outro backend)

---

## 🏗️ Arquitetura

Clean Architecture, com regra de dependência estrita entre camadas — o fluxo sempre aponta para baixo, nunca o contrário:

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

| Camada | Responsabilidade |
|---|---|
| `api/` | Recebe requisição HTTP, valida via Schema, chama o Service |
| `services/` | Toda a regra de negócio — nunca conhece detalhes de HTTP |
| `repositories/` | Único ponto de acesso a dados — sem regra de negócio |
| `models/` | Entidades persistidas (SQLAlchemy) |
| `schemas/` | Contratos de entrada/saída da API (Pydantic) |
| `security/` | JWT, hashing de senha, MFA, abstração de OAuth2 |
| `middleware/` | Rate limiting, logging estruturado, auditoria |
| `core/` | Configuração, logging, constantes, primitivas de segurança |

Detalhamento completo de cada camada e as regras de dependência entre elas: `docs/SPEC.md`.

---

## 📂 Estrutura do projeto

```text
auth-service/
├── alembic/              # migrações do banco de dados
├── app/
│   ├── api/              # controllers e injeção de dependências
│   ├── core/              # configuração, logging, constantes, criptografia
│   ├── database/          # engine SQLAlchemy, sessões
│   ├── exceptions/        # exceções de domínio e tradução para HTTP
│   ├── integrations/      # Redis, SMTP, providers OAuth
│   ├── middleware/        # rate limiting, logging, auditoria
│   ├── models/            # entidades (User, Role, Permission, ...)
│   ├── repositories/      # acesso a dados
│   ├── schemas/           # contratos da API
│   ├── security/          # JWT, hashing, MFA, OAuth2
│   ├── services/          # regras de negócio
│   └── main.py
├── tests/                # testes unitários, integração e API
├── docs/                 # guias de desenvolvimento, deploy, integração e uso
├── scripts/              # scripts operacionais (seed de permissões, etc.)
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 🔄 Fluxos principais

**Autenticação**
```text
Cliente → POST /login → AuthService
  → busca usuário → valida senha → verifica status da conta
  → gera access token + refresh token → cria sessão
  → resposta com access token e refresh token
```

**Autorização**
```text
Cliente → Authorization: Bearer <token> → Dependency
  → valida assinatura e expiração
  → carrega usuário, roles e permissions
  → libera o endpoint ou retorna 403
```

---

## 🔐 Segurança

Baseada nas recomendações da OWASP API Security Top 10, com:

- Senhas com hash e salt automático, nunca armazenadas em texto puro
- Refresh tokens rotacionados a cada uso, com detecção de reuso (revoga todas as sessões se detectado)
- Rate limiting por IP e bloqueio de conta após tentativas de login falhas
- Mensagens de erro de login que não revelam se um e-mail está cadastrado
- Logs de auditoria estruturados para todo evento sensível, sem nunca registrar senha ou token em texto puro
- Configuração inteira via variáveis de ambiente, com falha rápida na inicialização se algo obrigatório estiver ausente

---

## 🚀 Instalação rápida

O projeto roda inteiramente em containers (Docker ou Podman) — não precisa instalar Python, PostgreSQL ou Redis na sua máquina.

```bash
git clone https://github.com/<seu-usuario>/auth-service.git
cd auth-service
cp .env.example .env
# edite o .env e defina um JWT_SECRET_KEY forte (openssl rand -hex 32)
docker compose up --build
```

A API sobe em `http://localhost:8000`, com documentação interativa em `/docs`.

Guia completo — pré-requisitos (Docker Desktop, Docker Engine ou Podman), configuração, testes, migrações e solução de problemas: **[`docs/development-guide.md`](docs/development-guide.md)**.

---

## 🧪 Testes

```bash
docker compose --profile test run --rm test
```

Cobertura de testes unitários (services/security, com mocks), integração (repositórios contra banco real) e API (fluxos HTTP completos, incluindo os principais casos de borda de segurança). CI via GitHub Actions, rodando lint, checagem de tipos e a suíte completa em cada push e pull request.

---

## 📚 Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/SPEC.md`](docs/SPEC.md) | Especificação técnica completa: arquitetura, modelagem de dados, contrato de endpoints |
| [`docs/development-guide.md`](docs/development-guide.md) | Rodando e desenvolvendo localmente |
| [`docs/deployment-guide.md`](docs/deployment-guide.md) | Colocando em produção |
| [`docs/integration-guide.md`](docs/integration-guide.md) | Integrando outra aplicação a este serviço |
| [`docs/usage-guide.md`](docs/usage-guide.md) | O que a API faz, do ponto de vista funcional |
| [`docs/permissions-reference.md`](docs/permissions-reference.md) | Referência detalhada de cada permissão do RBAC |
| [`roadmap.md`](./roadmap.md) | O que já tem infraestrutura pronta no código mas ainda não está conectado a um endpoint e o que falta pra cobrir tudo. |
---

## 🛠️ Tecnologias

| Categoria | Stack |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL |
| Segurança | JWT, hashing de senha (bcrypt/argon2), RBAC, refresh tokens, MFA (TOTP) |
| Cache / Rate limiting | Redis |
| Infraestrutura | Docker / Podman, Docker Compose |
| Testes e qualidade | Pytest, Ruff, Mypy (strict), GitHub Actions |

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Abra uma *issue* descrevendo o problema/melhoria antes de codar.
2. Crie um branch a partir de `main`.
3. Rode o checklist de qualidade antes de commitar (`docs/development-guide.md`, seção 8) — o CI rejeita o PR se lint, tipos ou testes falharem.
4. Abra o Pull Request descrevendo o que mudou e por quê.

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes — uso livre em projetos pessoais, acadêmicos e comerciais.

---

## ⭐ Apoie o Projeto

Se este repositório foi útil para você, considere deixar uma **⭐ Star**.

Além de incentivar o projeto, isso ajuda outras pessoas a encontrarem este material.

---

<p align="center">

Desenvolvido com ❤️ para fortalecer a comunidade Backend.

**Aprender • Compartilhar • Evoluir**

</p>