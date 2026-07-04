# Guia de Uso — fluxos, ações e controle de acesso

Este documento explica **o que a API faz do ponto de vista de quem a usa**: quais ações existem, quem pode fazer o quê, e como o controle de acesso (RBAC) funciona na prática. Se você quer saber *como integrar* sua aplicação a este serviço, veja `docs/integration-guide.md`. Se quer saber *como colocar no ar*, veja `docs/deployment-guide.md`. Este aqui é sobre *o que o produto faz*.

---

## Sumário

- [1. Os dois tipos de "quem usa"](#1-os-dois-tipos-de-quem-usa)
- [2. Ciclo de vida de uma conta](#2-ciclo-de-vida-de-uma-conta)
- [3. Fluxo completo: usuário comum](#3-fluxo-completo-usuário-comum)
- [4. Como funciona o controle de acesso (RBAC)](#4-como-funciona-o-controle-de-acesso-rbac)
- [5. Fluxo completo: administrador](#5-fluxo-completo-administrador)
- [6. Sessões: o que são e como gerenciar](#6-sessões-o-que-são-e-como-gerenciar)
- [7. Tabela completa de endpoints e quem pode chamar cada um](#7-tabela-completa-de-endpoints-e-quem-pode-chamar-cada-um)
- [8. Perguntas frequentes](#8-perguntas-frequentes)

---

## 1. Os dois tipos de "quem usa"

| | Usuário comum | Administrador |
|---|---|---|
| Como se torna um | Se cadastra (`POST /auth/register`) | É um usuário comum promovido — atribuindo a ele uma role com as permissões certas, ou marcando `is_superuser=True` direto no banco |
| O que pode fazer | Gerenciar a própria conta: perfil, senha, sessões, MFA | Tudo que um usuário comum faz **+** gerenciar outros usuários, roles e permissões |
| Onde isso é decidido | Nenhuma configuração especial — é o padrão | RBAC (roles + permissions) — ver seção 4 |

Não existe um "tipo de conta administrador" fixo no banco — existe **RBAC**: um usuário vira administrador de fato quando alguém atribui a ele as permissões certas (ou o superpoder `is_superuser`, que ignora toda checagem de permissão). Ou seja, "admin" é uma composição de permissões, não um campo booleano simples (exceto o caso especial `is_superuser`, que é um atalho para "pode tudo").

---

## 2. Ciclo de vida de uma conta

Resumo de cada estado:

| Estado | `is_active` | `is_verified` | `deleted_at` | Pode logar? |
|---|---|---|---|---|
| Cadastro (aguardando e-mail) | `true` | `false` | `null` | Não — `ACCOUNT_NOT_VERIFIED` |
| Ativa | `true` | `true` | `null` | Sim |
| Bloqueada temporariamente | `true` | `true` | `null` | Não — `ACCOUNT_LOCKED`, até `locked_until` passar |
| Desativada | `false` | `true` | `null` | Não — `ACCOUNT_INACTIVE` |
| Excluída | — | — | *(preenchido)* | Não — tratada como inexistente pela API |

**Como cada transição acontece:**
- **Cadastro → Ativa**: usuário clica no link do e-mail de confirmação → `POST /auth/email/confirm`.
- **Ativa → Bloqueada**: `MAX_FAILED_LOGIN_ATTEMPTS` (padrão 5) tentativas de login com senha errada seguidas. Desbloqueio é automático, após `ACCOUNT_LOCKOUT_MINUTES` (padrão 15 minutos) — ninguém precisa agir manualmente.
- **Ativa → Desativada**: um administrador chama `POST /users/{id}/deactivate`. Só volta com `POST /users/{id}/activate`, também por um administrador.
- **Ativa → Excluída**: um administrador chama `DELETE /users/{id}` (exclusão lógica — o registro continua no banco para fins de auditoria, mas a API trata como se não existisse mais).

---

## 3. Fluxo completo: usuário comum

### 3.1. Cadastro e primeiro acesso

1. `POST /auth/register` com e-mail, nome e senha → conta criada, **não verificada**.
2. Um e-mail é enviado (ou, sem SMTP configurado em desenvolvimento, o token aparece no log) com um link de confirmação.
3. `POST /auth/email/confirm` com o token → conta vira **verificada**, pode logar.
4. `POST /auth/login` com e-mail e senha → recebe `access_token` (curta duração) + `refresh_token` (longa duração).

### 3.2. Uso do dia a dia

- Toda ação autenticada usa o `access_token` no header `Authorization: Bearer <token>`.
- Quando o `access_token` expira (padrão 15 minutos), usa-se `POST /auth/refresh` com o `refresh_token` para obter um par novo — sem precisar digitar senha de novo.
- `GET /users/me` — ver o próprio perfil.
- `PATCH /users/me` — editar o próprio nome.
- `PATCH /users/me/password` — trocar a própria senha (exige a senha atual).

### 3.3. Esqueci minha senha

1. `POST /auth/password/forgot` com o e-mail → sempre responde do mesmo jeito, exista ou não esse e-mail cadastrado (proteção contra descobrir quem tem conta).
2. Se existir, recebe um e-mail com token de redefinição.
3. `POST /auth/password/reset` com o token e a nova senha → senha trocada, **todas as sessões ativas são encerradas** (medida de segurança — se a senha precisou ser redefinida, pode ser porque foi comprometida).

### 3.4. Segurança extra (MFA)

1. `POST /auth/mfa/enable` (autenticado) → recebe um `secret` e a URI para escanear num app autenticador (Google Authenticator, Authy, etc).
2. A partir daí, todo login passa a exigir dois passos:
   - `POST /auth/login` com e-mail/senha → em vez do token de acesso, recebe um `challenge_token`.
   - `POST /auth/mfa/verify` com o `challenge_token` e o código de 6 dígitos do app → só então recebe o `access_token`/`refresh_token`.

### 3.5. Saindo

- `POST /auth/logout` — encerra só a sessão/dispositivo atual.
- `POST /auth/logout-all` — encerra **todas** as sessões em todos os dispositivos (útil se perder o celular, por exemplo).

---

## 4. Como funciona o controle de acesso (RBAC)

O modelo é: **usuário → tem roles → cada role tem permissions → cada endpoint administrativo exige uma permission específica.**

```text
Usuário "maria@loja.com"
   └── Role "gerente-estoque"
          ├── Permission "user:list"
          └── Permission "user:read"
```

Se Maria chama `GET /users` (que exige `user:list`), a API verifica: *alguma das roles de Maria tem a permission `user:list`?* Se sim, autorizado. Se não, `403 PERMISSION_DENIED`.

**Duas exceções a essa regra:**
1. **`is_superuser=True`** — ignora toda checagem de permissão, sempre autorizado. Use com moderação; é o "modo Deus" da conta.
2. **Ações sobre o próprio recurso** — algumas ações não passam por RBAC porque são sobre a *própria* conta do usuário, não sobre terceiros: `GET /users/me`, `PATCH /users/me`, `PATCH /users/me/password`, `GET /sessions` (mostra só as próprias sessões), `DELETE /sessions/{id}` (só revoga sessão que seja sua — tentar revogar a de outro usuário dá `403`, mesmo sendo uma checagem diferente do RBAC baseado em permissions).

### Permissões que já existem no sistema

Todas seguem o padrão `recurso:ação`:

| Permissão | Libera |
|---|---|
| `user:list` | `GET /users` |
| `user:read` | `GET /users/{id}` |
| `user:update` | `PATCH /users/{id}`, `POST /users/{id}/activate`, `POST /users/{id}/deactivate` |
| `user:delete` | `DELETE /users/{id}` |
| `role:list` / `role:read` / `role:create` / `role:update` / `role:delete` | CRUD de roles |
| `role:assign` | Atribuir/remover role de um usuário |
| `permission:list` / `permission:create` / `permission:update` / `permission:delete` | CRUD de permissões |
| `permission:assign` | Atribuir/remover permission de uma role |
| `session:list` / `session:revoke` | *(reservadas — hoje sessão só é gerenciada pelo próprio dono, sem endpoint administrativo separado)* |

Essas permissões já são criadas automaticamente pelo script `scripts/seed_permissions.py`, junto com uma role `admin` que já vem com todas elas atribuídas.

---

## 5. Fluxo completo: administrador

### 5.1. Virando administrador (feito uma vez, na configuração inicial)

Não existe um endpoint de "virar admin" — é uma ação de configuração de banco, feita conscientemente:

**Opção A — usando a role `admin` já criada pelo seed:**
```bash
POST /users/{seu_user_id}/roles
{"role_id": "<id da role admin>"}
```
(precisa ser feito por outro administrador, ou diretamente no banco na primeira vez, já que atribuir role exige a permissão `role:assign`)

**Opção B — modo Deus, direto no banco:**
```sql
UPDATE users SET is_superuser = true WHERE email = 'voce@example.com';
```

### 5.2. Gerenciando usuários

- `GET /users?page=1&page_size=20&search=maria` — lista paginada, com busca por nome/e-mail.
- `GET /users/{id}` — detalhe de um usuário específico.
- `PATCH /users/{id}` — editar nome/status de um usuário (não altera senha nem e-mail).
- `POST /users/{id}/activate` / `POST /users/{id}/deactivate` — ver ciclo de vida (seção 2).
- `DELETE /users/{id}` — exclusão lógica.

**Regra especial:** nenhum admin consegue desativar ou excluir a **própria** conta por esses endpoints (`409 CannotDeactivateSelfError`) — proteção contra se trancar fora do sistema sem querer.

### 5.3. Gerenciando roles e permissões

- `POST /roles` — cria uma role nova (ex: "atendente", "financeiro").
- `POST /roles/{role_id}/permissions` — atribui uma permissão a essa role.
- `POST /users/{user_id}/roles` — atribui essa role a um usuário.
- `POST /permissions` — cria uma permissão nova, se as pré-definidas não cobrirem seu caso (ex: `order:approve` para o gerenciador de entregas).

Fluxo típico pra dar acesso limitado a um funcionário — exemplo: "Maria pode ver a lista de clientes, mas não pode excluir ninguém":
```text
1. POST /roles                          {"name": "atendente"}
2. POST /roles/{id}/permissions          {"permission_id": "<id de user:list>"}
3. POST /roles/{id}/permissions          {"permission_id": "<id de user:read>"}
4. POST /users/{maria_id}/roles          {"role_id": "<id da role atendente>"}
```
A partir daí, Maria consegue `GET /users` e `GET /users/{id}`, mas `DELETE /users/{id}` continua dando `403` pra ela.

---

## 6. Sessões: o que são e como gerenciar

Cada **login bem-sucedido** cria uma `Session` — um registro de "esse dispositivo/navegador está logado", com IP e informação do dispositivo (`User-Agent`). É diferente de token: você pode ter uma sessão só, mas trocar de `access_token` várias vezes por hora (via refresh) — a sessão continua sendo a mesma até um logout ou expiração do refresh token.

- `GET /sessions` — lista todas as sessões ativas do usuário autenticado, marcando qual é a sessão da requisição atual (`is_current`).
- `DELETE /sessions/{id}` — revoga uma sessão específica (ex: "esqueci de sair do computador da biblioteca").

Isso é útil pra um usuário revisar "onde estou logado" e encerrar acessos que não reconhece — sem precisar trocar a senha inteira.

---

## 7. Tabela completa de endpoints e quem pode chamar cada um

| Endpoint | Autenticado? | Permissão exigida |
|---|---|---|
| `POST /auth/register` | Não | — |
| `POST /auth/login` | Não | — |
| `POST /auth/refresh` | Não (usa refresh token) | — |
| `POST /auth/logout` | Sim | — (própria sessão) |
| `POST /auth/logout-all` | Sim | — (próprias sessões) |
| `POST /auth/password/forgot` | Não | — |
| `POST /auth/password/reset` | Não (usa token de reset) | — |
| `POST /auth/email/confirm` | Não (usa token de confirmação) | — |
| `POST /auth/mfa/enable` | Sim | — (própria conta) |
| `POST /auth/mfa/verify` | Não (usa challenge token) | — |
| `GET /users/me` | Sim | — (própria conta) |
| `PATCH /users/me` | Sim | — (própria conta) |
| `PATCH /users/me/password` | Sim | — (própria conta) |
| `GET /users` | Sim | `user:list` |
| `GET /users/{id}` | Sim | `user:read` |
| `PATCH /users/{id}` | Sim | `user:update` |
| `DELETE /users/{id}` | Sim | `user:delete` |
| `POST /users/{id}/activate` | Sim | `user:update` |
| `POST /users/{id}/deactivate` | Sim | `user:update` |
| `POST /users/{id}/roles` | Sim | `role:assign` |
| `DELETE /users/{id}/roles/{role_id}` | Sim | `role:assign` |
| `POST /roles` | Sim | `role:create` |
| `GET /roles` | Sim | `role:list` |
| `GET /roles/{id}` | Sim | `role:read` |
| `PATCH /roles/{id}` | Sim | `role:update` |
| `DELETE /roles/{id}` | Sim | `role:delete` |
| `POST /roles/{id}/permissions` | Sim | `permission:assign` |
| `DELETE /roles/{id}/permissions/{id}` | Sim | `permission:assign` |
| `POST /permissions` | Sim | `permission:create` |
| `GET /permissions` | Sim | `permission:list` |
| `PATCH /permissions/{id}` | Sim | `permission:update` |
| `DELETE /permissions/{id}` | Sim | `permission:delete` |
| `GET /sessions` | Sim | — (próprias sessões) |
| `DELETE /sessions/{id}` | Sim | — (só a própria sessão, checado por posse, não por RBAC) |
| `GET /health` | Não | — |

Em todas as linhas com "Sim" + uma permissão: `is_superuser=True` sempre libera, independente da permissão listada.

---

## 8. Perguntas frequentes

**Um usuário sem nenhuma role consegue fazer alguma coisa administrativa?**
Não. Sem roles (ou `is_superuser`), ele só consegue gerenciar a própria conta — perfil, senha, sessões, MFA. Todo o resto retorna `403`.

**Dá pra ter várias roles ao mesmo tempo?**
Sim. As permissões de todas as roles de um usuário são somadas (união), não é preciso escolher uma só.

**O que acontece se eu excluir uma role que está atribuída a usuários?**
A role é removida do sistema e, com ela, a atribuição a qualquer usuário que a tinha — esses usuários perdem as permissões que só vinham dessa role. Não há confirmação extra nem aviso automático hoje — é uma ação que vale conferir antes de executar.

**Meu access token expira no meio de uma tarefa longa. O que acontece?**
A requisição em andamento não é interrompida (o token era válido quando a chamada começou), mas a **próxima** chamada com o token vencido recebe `401 TOKEN_EXPIRED` — nesse ponto, seu cliente deve chamar `/auth/refresh` (ver `docs/integration-guide.md`, seção 7, para o padrão de implementação).

**Como eu vejo quais permissões um usuário tem, sem entrar no banco?**
`GET /users/{id}` retorna o usuário com suas `roles`, e cada role já vem com suas `permissions` embutidas na resposta.
