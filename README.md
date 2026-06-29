# Auth Service

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)
![License](https://img.shields.io/badge/Licença-MIT-orange)
![Status](https://img.shields.io/badge/Status-Estável-success)
![Tests](https://img.shields.io/badge/Tests-Passing-success)
![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)

> Microsserviço de Autenticação e Autorização construído com FastAPI, projetado para ser plugado em qualquer sistema sem reescrever a camada de identidade.

---

## 📖 Visão Geral

O **Auth Service** é um microsserviço independente que resolve autenticação, autorização e gerenciamento de usuários de forma centralizada.

Em vez de reimplementar login, controle de acesso e gestão de identidade em cada novo projeto, este serviço assume essa responsabilidade por completo — permitindo que outras aplicações foquem exclusivamente em suas próprias regras de negócio.

Funciona tanto como uma **plataforma de autenticação pronta para produção** quanto como **template base** para novos projetos pessoais, acadêmicos e profissionais que precisem de uma fundação de identidade segura desde o primeiro dia.

A arquitetura foi construída em torno de cinco pilares:

- Segurança
- Escalabilidade
- Organização
- Manutenibilidade
- Reutilização

---

## ✨ Funcionalidades

### Autenticação
- Cadastro e login de usuários
- Logout (individual e em todos os dispositivos)
- Access Token e Refresh Token (JWT)
- Rotação automática de Refresh Tokens
- Recuperação e alteração de senha
- Confirmação de e-mail
- Gerenciamento de sessões com suporte a múltiplos dispositivos
- MFA (Autenticação Multifator)

### Autorização
- RBAC (Role-Based Access Control) completo
- Controle de permissões granulares
- Middleware de autorização e proteção de rotas
- Policies configuráveis

### Gestão de Usuários
- CRUD completo de usuários
- Ativação, desativação e exclusão lógica de contas
- Gerenciamento de perfil
- Políticas de senha configuráveis

### Segurança
- Hash seguro de senhas com salt automático
- Revogação de tokens
- Rate limiting e bloqueio por IP
- Proteção contra força bruta, credential stuffing e password spraying
- Auditoria e logs de segurança
- Validação de entrada, headers de segurança e cookies seguros
- Proteção contra CSRF e XSS

### Administração
- Gerenciamento de Roles e Permissions
- Administração de usuários e monitoramento de sessões
- Auditoria administrativa

---

## 🚀 Casos de Uso

O Auth Service é adequado para:

- APIs REST e arquiteturas em microsserviços
- Sistemas corporativos e plataformas SaaS
- Aplicações web, mobile e desktop
- Projetos pessoais e acadêmicos que precisam de uma base de autenticação sólida sem esforço extra

---

## ❓ Por que um microsserviço de autenticação?

Conforme uma aplicação cresce, manter autenticação acoplada ao sistema principal se torna um ponto de fricção. Separar essa responsabilidade em um serviço dedicado traz:

- Centralização da segurança
- Reutilização entre múltiplos projetos
- Escalabilidade e implantação independentes
- Padronização dos mecanismos de autenticação
- Gerenciamento centralizado de usuários
- Separação clara entre identidade e regras de negócio

---

## 🏗️ Arquitetura

A arquitetura segue princípios de **Clean Architecture** e **Domain-Oriented Design**, organizada em camadas com responsabilidades bem definidas. Cada camada depende apenas da camada imediatamente inferior — nunca o contrário.

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

### Princípios arquiteturais

- Separação de responsabilidades (Separation of Concerns)
- Clean Architecture e SOLID
- Dependency Injection
- Repository Pattern e Service Layer
- Programação defensiva e Fail Fast
- Segurança como decisão de design, não como adição posterior

### Responsabilidade de cada camada

| Camada | Responsabilidade |
|---------|------------------|
| API | Receber requisições HTTP |
| Dependencies | Autenticação e autorização |
| Services | Regras de negócio |
| Repositories | Persistência |
| Models | Entidades |
| Schemas | Contratos da API |
| Security | Infraestrutura de segurança |
| Middleware | Interceptação de requisições |
| Database | Conexão e sessões |
| Core | Configuração global |

> **Regra de dependência:** o fluxo sempre aponta para baixo (`API → Services → Repositories → Database`). Repositories nunca conhecem Services, e Services nunca conhecem detalhes de HTTP.

---

## 📂 Estrutura do Projeto

```text
auth-service/
│
├── alembic/                  # Migrações do banco de dados
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   ├── dependencies/
│   │   └── router.py
│   │
│   ├── core/                 # Configurações, logging, constantes
│   ├── database/             # Conexão e sessões
│   ├── middleware/           # Rate limiting, logging, auditoria
│   ├── models/                # Entidades (User, Role, Permission, ...)
│   ├── repositories/          # Acesso a dados
│   ├── schemas/               # Contratos da API
│   ├── security/               # JWT, hashing, MFA, OAuth2
│   ├── services/               # Regras de negócio
│   ├── utils/                  # Funções auxiliares genéricas
│   ├── exceptions/             # Tratamento centralizado de erros
│   ├── integrations/           # Redis, SMTP, OAuth Providers
│   └── main.py
│
├── tests/                    # Testes unitários, integração e API
├── docker/
├── docs/
├── scripts/
│
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 🔄 Fluxo de Autenticação

```text
Cliente → POST /login → API → AuthenticationService
  → busca usuário → valida senha
  → gera Access Token e Refresh Token → salva sessão
  → resposta com Access Token e Refresh Token
```

## 🔐 Fluxo de Autorização

```text
Cliente → Authorization: Bearer Token → Middleware
  → extrai token → valida assinatura → verifica expiração
  → carrega usuário, roles e permissions
  → valida acesso → Endpoint
```

---

## 🔒 Segurança

A segurança segue o princípio **Security by Design** e as recomendações da **OWASP**, com:

- Menor Privilégio e Defesa em Profundidade
- Secure by Default, Fail Fast e Fail Secure
- Validação de todas as entradas — nunca confiar no cliente

**Autenticação** baseada em JWT, com Access Token, Refresh Token, rotação e revogação de tokens, controle de sessões simultâneas e logout em todos os dispositivos.

**Autorização** baseada em RBAC:

```text
Usuário → Role → Permissions → Recurso protegido
```

**Senhas** nunca armazenadas em texto puro — hash seguro com salt automático, políticas de senha e expiração configurável.

**Proteções implementadas** contra Brute Force, Credential Stuffing, Password Spraying, Token Replay, Session Hijacking, CSRF, XSS, SQL Injection e Enumeration Attacks.

**Auditoria** de eventos críticos: login, logout, alteração de senha, criação de usuários, alteração de permissões, revogação de tokens e tentativas de acesso inválidas.

**Configuração** via variáveis de ambiente — nenhuma informação sensível (secrets, credenciais, chaves privadas) é armazenada no código.

---

## 🚀 Instalação

### Clonando o projeto

```bash
git clone https://github.com/<usuario>/auth-service.git
cd auth-service
```

### Criando o ambiente virtual

```bash
python -m venv .venv
```

**Windows**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**
```bash
source .venv/bin/activate
```

### Instalando dependências

```bash
pip install -U pip
pip install -r requirements.txt
```

### Configurando variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com os valores do seu ambiente (banco de dados, secrets, SMTP, OAuth, etc).

### Executando migrações

```bash
alembic upgrade head
```

### Executando a aplicação

```bash
uvicorn app.main:app --reload
```

### Executando com Docker

```bash
docker-compose up --build
```

---

## 🧪 Testes

O projeto possui cobertura de testes unitários, de integração, de API e de segurança.

```bash
pytest
```

CI configurado via **GitHub Actions**, executando automaticamente lint, type-checking e a suíte de testes em cada push e pull request.

---

## 📚 Tecnologias

| Categoria | Stack |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Segurança | JWT, Password Hashing, RBAC, Refresh Tokens, MFA, OAuth2, OpenID Connect |
| Infraestrutura | Docker, Docker Compose |
| Observabilidade | OpenTelemetry, Métricas |
| Ferramentas | Pytest, Ruff, Mypy, GitHub Actions |

---

## 🎓 Conceitos Aplicados

Este projeto é também uma referência prática sobre:

- Arquitetura de Microsserviços e Clean Architecture
- Segurança de APIs seguindo recomendações OWASP
- Autenticação (JWT) e Autorização (RBAC)
- FastAPI, SQLAlchemy, Alembic e PostgreSQL em produção
- Testes automatizados e pipelines de CI/CD

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Faça push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

Sugestões, correções e melhorias podem ser enviadas via Issues e Pull Requests.

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes — uso livre em projetos pessoais, acadêmicos e comerciais.

---

## 🌟 Considerações Finais

O Auth Service elimina a necessidade de reconstruir a infraestrutura de autenticação em cada novo projeto. Mais do que uma API de login, é uma plataforma completa de autenticação e autorização, pronta para servir como base de aplicações modernas ou como template para acelerar o início de novos sistemas — sem abrir mão de segurança, escalabilidade ou boas práticas de engenharia.
