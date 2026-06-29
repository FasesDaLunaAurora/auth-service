
# Auth Service

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)
![License](https://img.shields.io/badge/Licença-MIT-orange)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow)

> Microsserviço de Autenticação e Autorização desenvolvido com FastAPI.
>
> **Objetivo:** fornecer uma base reutilizável, segura e escalável para aplicações modernas.

---

# 📖 Visão Geral

O **Auth Service** é um microsserviço independente responsável pela autenticação e autorização de usuários.

Ao invés de implementar login, controle de acesso e gerenciamento de usuários em cada novo projeto, este serviço centraliza toda a gestão de identidade, permitindo que outros sistemas foquem exclusivamente em suas regras de negócio.

O projeto está sendo desenvolvido para servir tanto como uma plataforma de autenticação completa quanto como um template reutilizável para novos projetos pessoais, acadêmicos e profissionais.

Desde o início, a arquitetura é pensada com foco em:

- Segurança
- Escalabilidade
- Organização
- Facilidade de manutenção
- Reutilização
- Boas práticas de engenharia de software

Embora inicialmente seja um projeto de portfólio, a visão de longo prazo é torná-lo uma referência open source para autenticação e autorização utilizando Python e FastAPI.

---

# 🎯 Objetivos

O Auth Service possui cinco objetivos principais.

## 1. Centralizar autenticação

Todo o processo de autenticação deve estar concentrado em um único serviço.

Isso evita duplicação de código entre aplicações e facilita futuras evoluções.

---

## 2. Centralizar autorização

O serviço será responsável por controlar permissões, papéis (Roles) e políticas de acesso, permitindo que outras APIs apenas consultem se determinado usuário possui autorização para executar determinada ação.

---

## 3. Servir como template

O projeto deverá ser reutilizável.

A ideia é que futuros sistemas possam utilizar este repositório como base para autenticação sem precisar reimplementar toda a infraestrutura de segurança.

---

## 4. Demonstrar arquitetura moderna

Além de resolver um problema real, o projeto pretende demonstrar conhecimentos em:

- Arquitetura em Camadas
- Microsserviços
- Clean Architecture
- Segurança
- FastAPI
- SQLAlchemy
- PostgreSQL
- Testes
- Docker
- CI/CD

---

## 5. Tornar-se uma referência de estudo

Após atingir estabilidade, o projeto será disponibilizado publicamente para servir como material de estudo sobre autenticação, autorização e arquitetura backend.

---

# 💡 Filosofia do Projeto

O desenvolvimento do Auth Service é guiado por alguns princípios fundamentais.

## Autenticação não é regra de negócio

Autenticação deve existir independentemente da aplicação.

Cada sistema deve concentrar seus esforços em resolver seu próprio domínio, delegando autenticação e autorização para um serviço especializado.

---

## Segurança desde o início

A segurança não deve ser adicionada posteriormente.

Ela faz parte das decisões arquiteturais desde o primeiro commit.

Cada nova funcionalidade será desenvolvida considerando princípios como:

- Confidencialidade
- Integridade
- Disponibilidade
- Menor Privilégio
- Defesa em Profundidade
- Secure by Default

---

## Separação de responsabilidades

Cada camada do sistema deve possuir uma responsabilidade claramente definida.

Nenhum componente deve conhecer detalhes que pertencem a outra camada.

Essa separação facilita:

- manutenção;
- testes;
- evolução;
- reutilização de código.

---

## Extensibilidade

A arquitetura deve permitir adicionar novos mecanismos de autenticação sem necessidade de grandes refatorações.

Entre as funcionalidades planejadas estão:

- OAuth2
- OpenID Connect
- API Keys
- Passkeys
- MFA (Autenticação Multifator)
- Login Social

---

## Reutilização

Este projeto não é apenas uma API de login.

Ele deve se tornar um componente reutilizável em diversos projetos futuros.

Idealmente, uma nova aplicação deverá conseguir utilizar o Auth Service sem precisar modificar seu núcleo.

---

## Simplicidade

Sempre que possível, soluções simples terão prioridade sobre soluções excessivamente complexas.

Código legível é mais importante que código "inteligente".

---

# ✨ Funcionalidades Planejadas

## Autenticação

- Cadastro de usuários
- Login
- Logout
- Access Token
- Refresh Token
- Rotação de Refresh Tokens
- Recuperação de senha
- Alteração de senha
- Confirmação de e-mail
- Gerenciamento de sessões
- Suporte a múltiplos dispositivos
- MFA (planejado)

---

## Autorização

- RBAC (Role-Based Access Control)
- Controle de permissões
- Proteção de rotas
- Middleware de autorização
- Permissões granulares
- Policies (planejado)

---

## Gestão de Usuários

- CRUD de usuários
- Ativação de contas
- Desativação de contas
- Exclusão lógica
- Gerenciamento de perfil
- Políticas de senha

---

## Segurança

- JWT
- Rotação de Refresh Tokens
- Revogação de Tokens
- Hash seguro de senhas
- Rate Limiting
- Bloqueio por IP
- Proteção contra força bruta
- Auditoria
- Logs de segurança
- Validação de entrada
- Headers de segurança
- Cookies seguros (quando aplicável)
- Proteção contra CSRF (quando aplicável)

---

## Administração

- Gerenciamento de Roles
- Gerenciamento de Permissões
- Administração de usuários
- Monitoramento de sessões
- Auditoria administrativa
- Configuração do sistema

---

# 🚀 Casos de Uso

O Auth Service foi projetado para atender diferentes cenários.

Entre eles:

- APIs REST
- Arquiteturas em Microsserviços
- Sistemas Corporativos
- Plataformas SaaS
- Aplicações Web
- Backends para Aplicações Mobile
- Aplicações Desktop
- Projetos pessoais
- Projetos acadêmicos

---

# ❓ Por que um microsserviço de autenticação?

Conforme uma aplicação cresce, manter autenticação integrada ao sistema principal torna-se cada vez mais difícil.

Separar autenticação em um serviço dedicado oferece diversos benefícios:

- Centralização da segurança;
- Reutilização entre projetos;
- Facilidade de manutenção;
- Escalabilidade independente;
- Implantação independente;
- Padronização dos mecanismos de autenticação;
- Gerenciamento centralizado de usuários;
- Separação clara entre autenticação e regras de negócio.

---

# 🌍 Visão de Longo Prazo

A proposta do Auth Service é evoluir para uma plataforma completa de autenticação e autorização que possa ser utilizada em diferentes ecossistemas de software.

Ao invés de recriar autenticação para cada novo projeto, bastará integrar este serviço para obter:

- autenticação segura;
- autorização centralizada;
- gerenciamento de usuários;
- gerenciamento de sessões;
- controle de permissões;
- boas práticas modernas de segurança.

Além disso, o projeto pretende servir como referência para desenvolvedores interessados em aprender autenticação moderna utilizando FastAPI.

---

# 🚧 Status do Projeto

> **Status atual:** Em desenvolvimento.

A arquitetura ainda está em construção e mudanças estruturais são esperadas até a primeira versão estável.

Durante essa fase, o foco está em estabelecer uma base sólida que permita futuras expansões sem necessidade de grandes refatorações.

---

# 📌 Princípios do Projeto

Toda implementação deve respeitar os seguintes princípios:

- Segurança em primeiro lugar;
- Clean Architecture;
- SOLID;
- Dependency Injection;
- Repository Pattern;
- Arquitetura em Camadas;
- Tipagem forte;
- Código explícito;
- Alta testabilidade;
- Programação defensiva;
- Recomendações OWASP;
- Facilidade de manutenção.

Esses princípios servirão como guia para todas as decisões arquiteturais tomadas durante o desenvolvimento do projeto.

---

# 🏗️ Arquitetura

A arquitetura do Auth Service foi projetada para ser modular, extensível e de fácil manutenção.

Embora o projeto seja inicialmente um único microsserviço, sua organização segue princípios utilizados em sistemas distribuídos e aplicações corporativas.

O objetivo é que novas funcionalidades possam ser adicionadas sem comprometer a estabilidade das existentes.

---

# 🧱 Princípios Arquiteturais

O desenvolvimento do projeto segue os seguintes princípios:

- Separação de responsabilidades (Separation of Concerns)
- Clean Architecture
- SOLID
- Dependency Injection
- Repository Pattern
- Service Layer
- Domain-Oriented Design
- Programação Defensiva
- Fail Fast
- Segurança em primeiro lugar

Esses princípios reduzem o acoplamento entre componentes e facilitam testes, manutenção e evolução do sistema.

---

# 🏛️ Visão Geral da Arquitetura

```text
                           Cliente

                               │
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

Cada camada possui responsabilidades bem definidas e depende apenas da camada imediatamente inferior.

---

# 📂 Estrutura do Projeto

```text
auth-service/

│
├── alembic/                  # Migrações do banco de dados
│
├── app/
│
│   ├── api/
│   │   ├── routes/
│   │   ├── dependencies/
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
│   │
│   ├── models/
│   │
│   ├── repositories/
│   │
│   ├── schemas/
│   │
│   ├── security/
│   │
│   ├── services/
│   │
│   ├── utils/
│   │
│   ├── exceptions/
│   │
│   ├── integrations/
│   │
│   └── main.py
│
├── tests/
│
├── docker/
│
├── docs/
│
├── scripts/
│
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# 📦 Organização das Camadas

## API

Responsável por receber requisições HTTP.

Nesta camada ficam:

- Endpoints
- Validação inicial
- Conversão Request → DTO
- Conversão DTO → Response

A API nunca implementa regras de negócio.

---

## Services

É o coração da aplicação.

Toda regra de negócio deve existir nesta camada.

Exemplos:

- Login
- Cadastro
- Alteração de senha
- Revogação de Token
- Criação de usuários
- Validação de permissões

Services nunca conhecem HTTP.

---

## Repositories

Responsáveis exclusivamente pelo acesso aos dados.

Suas responsabilidades incluem:

- SELECT
- INSERT
- UPDATE
- DELETE

Repositories nunca conhecem regras de negócio.

---

## Models

Representam as entidades persistidas no banco.

Exemplos:

- User
- Role
- Permission
- RefreshToken
- Session

---

## Schemas

Representam os contratos da API.

Exemplos:

- LoginRequest
- LoginResponse
- UserCreate
- UserUpdate

Schemas nunca representam tabelas.

---

## Security

Contém toda infraestrutura relacionada à segurança.

Exemplos:

- JWT
- Password Hashing
- MFA
- OAuth2
- API Keys
- Token Validation

---

## Middleware

Responsável por interceptar requisições.

Exemplos:

- Rate Limiting
- Logging
- Auditoria
- Tempo de resposta
- Correlação de requisições

---

## Core

Contém configurações compartilhadas por todo o sistema.

Exemplos:

- Configurações
- Variáveis de ambiente
- Logging
- Constantes
- Inicialização

---

## Utils

Funções auxiliares reutilizáveis.

Devem conter apenas código genérico.

Nunca regras de negócio.

---

## Exceptions

Centraliza todas as exceções da aplicação.

Objetivos:

- padronização;
- mensagens consistentes;
- tratamento centralizado.

---

## Integrations

Integrações com serviços externos.

Exemplos futuros:

- Redis
- RabbitMQ
- SMTP
- OpenTelemetry
- OAuth Providers

---

# 🔄 Fluxo de Autenticação

```text
Cliente

   │

   │ POST /login

   ▼

API

   │

Validação do Request

   │

   ▼

AuthenticationService

   │

Busca usuário

   │

Valida senha

   │

Gera Access Token

   │

Gera Refresh Token

   │

Salva Sessão

   │

   ▼

Resposta

Access Token

Refresh Token
```

---

# 🔐 Fluxo de Autorização

```text
Cliente

   │

Authorization: Bearer Token

   │

   ▼

Middleware

   │

Extrai Token

   │

Valida Assinatura

   │

Verifica Expiração

   │

Carrega Usuário

   │

Carrega Roles

   │

Carrega Permissions

   │

Valida acesso

   │

   ▼

Endpoint
```

---

# 🧩 Comunicação entre Camadas

```text
HTTP

↓

Router

↓

Dependency

↓

Service

↓

Repository

↓

Database
```

O fluxo sempre deve seguir esta direção.

Camadas inferiores nunca chamam camadas superiores.

---

# 📐 Responsabilidade de Cada Camada

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

---

# 🔄 Princípio da Dependência

As dependências sempre apontam para o domínio da aplicação.

Exemplo correto:

```text
API
 ↓
Services
 ↓
Repositories
 ↓
Database
```

Exemplo incorreto:

```text
Repository
      ↓
Service
```

Repositories nunca devem conhecer Services.

---

# 🧪 Estratégia de Testes

A arquitetura foi planejada para facilitar testes automatizados.

Serão utilizados:

- Testes unitários
- Testes de integração
- Testes de API
- Testes de autenticação
- Testes de autorização
- Testes de segurança

Cada camada poderá ser testada de forma independente.

---

# 📈 Escalabilidade

O projeto foi estruturado para permitir futuras expansões sem alterações significativas na arquitetura.

Algumas evoluções previstas incluem:

- Redis para cache
- Filas com RabbitMQ
- Revogação distribuída de tokens
- Múltiplos bancos de dados
- Observabilidade
- Métricas
- Kubernetes
- Balanceamento de carga
- Horizontal Scaling

A arquitetura busca minimizar acoplamentos para que essas evoluções ocorram de maneira incremental.

---


# 🔒 Segurança

A segurança é o principal objetivo deste projeto.

Toda funcionalidade implementada deve seguir o princípio **Security by Design**, considerando a segurança desde sua concepção e não apenas como uma etapa final do desenvolvimento.

O projeto busca seguir as recomendações da **OWASP**, padrões modernos de autenticação e boas práticas utilizadas em aplicações corporativas.

---

# 🛡️ Princípios de Segurança

Toda implementação deve respeitar os seguintes princípios:

- Menor Privilégio (Least Privilege)
- Defesa em Profundidade (Defense in Depth)
- Secure by Default
- Fail Fast
- Fail Secure
- Princípio da Responsabilidade Única
- Validação de todas as entradas
- Nunca confiar no cliente

---

# 🔑 Autenticação

O mecanismo principal de autenticação será baseado em JWT.

Funcionalidades previstas:

- Login
- Logout
- Access Token
- Refresh Token
- Rotação de Refresh Tokens
- Revogação de Tokens
- Controle de sessões
- Logout em todos os dispositivos
- Sessões simultâneas configuráveis

---

# 👤 Autorização

A autorização será baseada em **RBAC (Role-Based Access Control)**.

Exemplo:

```text
Usuário

↓

Role

↓

Permissions

↓

Recurso protegido
```

Cada usuário poderá possuir uma ou mais Roles.

Cada Role poderá possuir diversas permissões.

As permissões serão utilizadas para controlar o acesso aos recursos da aplicação.

---

# 🔐 Proteção de Senhas

As senhas nunca serão armazenadas em texto puro.

O projeto utilizará algoritmos modernos de hash criptográfico.

Planejamento:

- Hash seguro
- Salt automático
- Políticas de senha
- Expiração configurável
- Histórico de senhas (futuro)

---

# 🚨 Proteções Previstas

O projeto pretende implementar mecanismos para proteção contra diversos ataques.

Entre eles:

- Brute Force
- Credential Stuffing
- Password Spraying
- Token Replay
- Session Hijacking
- CSRF
- XSS
- SQL Injection
- Enumeration Attacks

---

# 📊 Auditoria

Eventos importantes deverão ser registrados.

Exemplos:

- Login
- Logout
- Alteração de senha
- Criação de usuários
- Alteração de permissões
- Revogação de Tokens
- Tentativas de acesso inválidas

---

# ⚙️ Configuração

O projeto será configurado por variáveis de ambiente.

Nenhuma informação sensível deverá ser armazenada diretamente no código.

Exemplos:

- Secret Keys
- Credenciais do banco
- Configuração SMTP
- Configuração OAuth
- Chaves privadas

---

# 🚀 Instalação

## Clonando o projeto

```bash
git clone https://github.com/<usuario>/auth-service.git

cd auth-service
```

---

## Criando ambiente virtual

```bash
python -m venv .venv
```

Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux

```bash
source .venv/bin/activate
```

---

## Instalando dependências

```bash
pip install -U pip

pip install -r requirements.txt
```

---

## Configurando variáveis de ambiente

```bash
cp .env.example .env
```

Configure os valores conforme seu ambiente.

---

## Executando migrações

```bash
alembic upgrade head
```

---

## Executando a aplicação

```bash
uvicorn app.main:app --reload
```

---

# 🧪 Testes

Os testes poderão ser executados utilizando:

```bash
pytest
```

Também serão previstos:

- Testes Unitários
- Testes de Integração
- Testes de API
- Testes de Segurança

---

# 📚 Tecnologias

## Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

---

## Segurança

- JWT
- Password Hashing
- RBAC
- Refresh Tokens

---

## Infraestrutura

- Docker
- Docker Compose

---

## Ferramentas

- Pytest
- Ruff
- Mypy
- GitHub Actions

---

# 🛣️ Roadmap

## MVP

- [ ] Cadastro de usuários
- [ ] Login
- [ ] Logout
- [ ] JWT
- [ ] Refresh Token
- [ ] CRUD de usuários
- [ ] Roles
- [ ] Permissions
- [ ] Alembic
- [ ] Docker

---

## Versão 1.0

- [ ] Recuperação de senha
- [ ] Confirmação de e-mail
- [ ] Auditoria
- [ ] Rate Limiting
- [ ] Bloqueio por IP
- [ ] Sessões

---

## Versão 2.0

- [ ] MFA
- [ ] OAuth2
- [ ] OpenID Connect
- [ ] API Keys
- [ ] Redis
- [ ] Cache distribuído

---

## Versão 3.0

- [ ] Observabilidade
- [ ] Métricas
- [ ] OpenTelemetry
- [ ] Kubernetes
- [ ] Alta disponibilidade

---

# 🎓 Objetivos de Aprendizado

Este projeto explora diversos conceitos importantes do desenvolvimento backend moderno, incluindo:

- Arquitetura de Microsserviços
- Segurança de APIs
- Autenticação
- Autorização
- JWT
- RBAC
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Docker
- Testes Automatizados
- CI/CD
- Boas práticas OWASP

---

# 🤝 Contribuições

Enquanto o projeto estiver em desenvolvimento, o repositório permanecerá privado.

Após atingir uma versão estável, contribuições da comunidade serão muito bem-vindas.

Sugestões, correções e melhorias poderão ser enviadas através de Issues e Pull Requests.

---

# 📄 Licença

Este projeto será distribuído sob a licença **MIT**.

Isso permitirá seu uso em projetos pessoais, acadêmicos e comerciais, respeitando os termos da licença.

---

# 🌟 Considerações Finais

O Auth Service nasceu com o objetivo de eliminar a necessidade de reconstruir a infraestrutura de autenticação em cada novo projeto.

Mais do que uma API de login, este repositório pretende evoluir para uma plataforma completa de autenticação e autorização, servindo como base para aplicações modernas e como referência de estudo sobre arquitetura, segurança e desenvolvimento backend com Python.

A expectativa é que, ao atingir maturidade, este projeto possa ser utilizado como template em novos sistemas, reduzindo o tempo de desenvolvimento e incentivando a adoção de boas práticas desde o início.

---


