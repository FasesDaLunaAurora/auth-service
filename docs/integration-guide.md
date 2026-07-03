# Guia de Integração — conectando sua aplicação ao Auth Service

Este documento explica como uma aplicação cliente (frontend, backend, ou ambos) deve se integrar ao Auth Service para delegar autenticação, autorização (RBAC) e gestão de sessões, em vez de reimplementar isso internamente.

---

## Sumário

- [1. Modelo de integração](#1-modelo-de-integração)
- [2. Pré-requisitos de configuração](#2-pré-requisitos-de-configuração)
- [3. Fluxo de cadastro e confirmação de e-mail](#3-fluxo-de-cadastro-e-confirmação-de-e-mail)
- [4. Fluxo de login (com e sem MFA)](#4-fluxo-de-login-com-e-sem-mfa)
- [5. Onde e como guardar os tokens no cliente](#5-onde-e-como-guardar-os-tokens-no-cliente)
- [6. Anexando o access token nas requisições](#6-anexando-o-access-token-nas-requisições)
- [7. Renovando o token automaticamente (refresh)](#7-renovando-o-token-automaticamente-refresh)
- [8. Logout](#8-logout)
- [9. Aplicando RBAC no lado do cliente](#9-aplicando-rbac-no-lado-do-cliente)
- [10. Dois padrões de integração backend-a-backend](#10-dois-padrões-de-integração-backend-a-backend)
- [11. CORS](#11-cors)
- [12. Checklist de segurança](#12-checklist-de-segurança)
- [13. Erros comuns e como tratá-los](#13-erros-comuns-e-como-tratá-los)

---

## 1. Modelo de integração

O Auth Service é a **única fonte de verdade** para identidade, credenciais e permissões. Sua aplicação (o "cliente") nunca deve:

- Armazenar senhas de usuários.
- Implementar sua própria lógica de hash/verificação de senha.
- Decidir sozinha se um usuário está "logado" — isso é sempre validado via token emitido pelo Auth Service.

O fluxo geral é:

```text
┌──────────────┐        1. login/register         ┌──────────────┐
│              │ ────────────────────────────────▶│              │
│  Sua App     │                                   │ Auth Service │
│ (frontend ou │ ◀──────────────────────────────── │              │
│  backend)    │      2. access + refresh token    │              │
│              │                                   │              │
│              │  3. requisições autenticadas       │              │
│              │    (Authorization: Bearer <token>) │              │
│              │ ────────────────────────────────▶ │              │
└──────────────┘                                   └──────────────┘
```

Sua aplicação guarda os tokens emitidos e os reenvia a cada requisição — tanto para chamar o próprio Auth Service (ex: `GET /users/me`) quanto, se for o caso, para autenticar chamadas à **sua própria API de backend** (ver [seção 10](#10-dois-padrões-de-integração-backend-a-backend)).

---

## 2. Pré-requisitos de configuração

Antes de integrar, confirme com quem administra o Auth Service:

1. **URL base** do serviço (ex: `https://auth.suaempresa.com/api/v1` ou `http://localhost:8000/api/v1` em desenvolvimento).
2. **Origem do seu frontend registrada em `CORS_ALLOWED_ORIGINS`** (ver [seção 11](#11-cors)) — sem isso, o navegador bloqueia as requisições.
3. **Permissões e roles já existentes** (via `scripts/seed_permissions.py`) que fazem sentido para o seu caso de uso, ou solicite a criação de novas via `POST /roles` / `POST /permissions` (requer permissão administrativa).
4. Decida se seu caso de uso precisa de **MFA obrigatório** para certos perfis de usuário — o Auth Service suporta, mas habilitar é uma ação por usuário (`POST /auth/mfa/enable`), não uma política global automática.

---

## 3. Fluxo de cadastro e confirmação de e-mail

```text
Cliente                          Auth Service
   │                                   │
   │  POST /auth/register              │
   │ ─────────────────────────────────▶│
   │                                   │  cria usuário (is_verified=false)
   │                                   │  envia e-mail com token de confirmação
   │  201 { id, email, is_verified }   │
   │ ◀───────────────────────────────  │
   │                                   │
   │  (usuário clica no link do e-mail)│
   │                                   │
   │  POST /auth/email/confirm         │
   │  { token }                        │
   │ ─────────────────────────────────▶│
   │  204 No Content                   │
   │ ◀───────────────────────────────  │
```

Pontos importantes:
- **Login falha com 403 (`ACCOUNT_NOT_VERIFIED`) até a confirmação de e-mail.** Trate esse código de erro explicitamente na sua tela de login, oferecendo reenviar a confirmação (o Auth Service não expõe um endpoint de "reenviar" — hoje é necessário registrar de novo ou pedir suporte administrativo para confirmar manualmente).
- O link de confirmação de e-mail deve apontar para uma página **da sua aplicação**, que extrai o `token` da URL e faz o `POST /auth/email/confirm` — o Auth Service não serve HTML, só JSON.

Exemplo de página de confirmação (frontend):

```javascript
// Rota da sua app: /confirmar-email?token=xxxxx
const token = new URLSearchParams(window.location.search).get("token");

const response = await fetch("https://auth.suaempresa.com/api/v1/auth/email/confirm", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ token }),
});

if (response.status === 204) {
  // redirecione para a tela de login com uma mensagem de sucesso
} else {
  // token inválido ou expirado — ofereça registrar novamente
}
```

---

## 4. Fluxo de login (com e sem MFA)

```text
Cliente                          Auth Service
   │                                   │
   │  POST /auth/login                 │
   │  { email, password }              │
   │ ─────────────────────────────────▶│
   │                                   │
   │        ┌──────────────────────────┴───────────────────────┐
   │        │ Conta SEM MFA                                     │
   │  200 { access_token, refresh_token, token_type, expires_in}│
   │ ◀──────┤                                                   │
   │        │ Conta COM MFA ativo                                │
   │  200 { mfa_required: true, challenge_token }               │
   │ ◀──────┴───────────────────────────────────────────────────┘
   │                                   │
   │  (se mfa_required) usuário digita o código do app autenticador
   │                                   │
   │  POST /auth/mfa/verify            │
   │  { challenge_token, code }        │
   │ ─────────────────────────────────▶│
   │  200 { access_token, refresh_token, ... }
   │ ◀───────────────────────────────  │
```

O corpo de `POST /auth/login` retorna **um de dois formatos possíveis** — sua aplicação precisa checar a presença de `mfa_required` para decidir qual tela mostrar:

```javascript
async function login(email, password) {
  const response = await fetch(`${AUTH_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const body = await response.json();

  if (!response.ok) {
    throw new Error(body.error?.message ?? "Falha no login");
  }

  if (body.mfa_required) {
    // Guarde `body.challenge_token` em memória (não em storage
    // persistente) e mostre a tela de "digite o código do app".
    return { requiresMfa: true, challengeToken: body.challenge_token };
  }

  // Login concluído — guarde os tokens (ver seção 5).
  return { requiresMfa: false, tokens: body };
}

async function verifyMfa(challengeToken, code) {
  const response = await fetch(`${AUTH_BASE_URL}/auth/mfa/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_token: challengeToken, code }),
  });
  if (!response.ok) throw new Error("Código inválido");
  return await response.json(); // { access_token, refresh_token, ... }
}
```

---

## 5. Onde e como guardar os tokens no cliente

| Tipo de cliente | Recomendação |
|---|---|
| **SPA (React/Vue/etc.) servida por um domínio separado do backend** | Guarde o `access_token` em memória (variável JS / estado da aplicação), **não** em `localStorage` — evita exposição a XSS. Para persistir entre recarregamentos de página sem forçar novo login, use o `refresh_token` guardado em um cookie `httpOnly` + `Secure` + `SameSite=Strict`, setado pelo **seu próprio backend** (não pelo Auth Service diretamente) após um proxy de login. |
| **Aplicação com backend próprio renderizando páginas (SSR/MVC tradicional)** | O backend da sua aplicação chama o Auth Service, recebe os tokens, e os guarda em cookie `httpOnly` da sessão do seu próprio domínio. O JS do navegador nunca vê o token diretamente. |
| **Aplicativo mobile** | Guarde em armazenamento seguro nativo (Keychain no iOS, Keystore no Android) — nunca em `AsyncStorage`/preferências simples sem criptografia. |
| **Serviço backend-a-backend (sem usuário navegando)** | Guarde em variável de ambiente/secret manager, nunca em código-fonte ou logs. |

**Nunca**, em nenhum cenário, guarde o `refresh_token` em `localStorage` ou `sessionStorage` acessível via JavaScript — ele tem validade de dias (`REFRESH_TOKEN_EXPIRE_DAYS`), então um XSS que o rouba compromete a conta por muito mais tempo que um access token (que expira em minutos).

---

## 6. Anexando o access token nas requisições

Toda rota autenticada do Auth Service (e, tipicamente, do seu próprio backend, se ele também validar o token) espera:

```http
Authorization: Bearer <access_token>
```

Exemplo:

```javascript
async function getMe(accessToken) {
  const response = await fetch(`${AUTH_BASE_URL}/users/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (response.status === 401) {
    // token expirado ou inválido — ver seção 7 (refresh)
  }
  return await response.json();
}
```

---

## 7. Renovando o token automaticamente (refresh)

O `access_token` expira rápido (`ACCESS_TOKEN_EXPIRE_MINUTES`, padrão 15 min) de propósito — é o `refresh_token` (padrão 7 dias) que mantém a sessão viva sem pedir senha de novo. Implemente um **interceptor** que:

1. Detecta uma resposta `401`.
2. Chama `POST /auth/refresh` com o `refresh_token` guardado.
3. Se o refresh funcionar, repete a requisição original com o novo `access_token`.
4. Se o refresh **também** falhar (401), a sessão realmente acabou — redirecione para o login.

Exemplo com `fetch` (padrão "fila de requisições" para evitar múltiplos refreshes simultâneos):

```javascript
let refreshPromise = null;

async function authorizedFetch(url, options = {}) {
  let accessToken = getStoredAccessToken();

  const doFetch = (token) =>
    fetch(url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    });

  let response = await doFetch(accessToken);

  if (response.status === 401) {
    // Evita disparar N refreshes em paralelo se N requisições
    // falharem ao mesmo tempo — todas esperam a mesma promise.
    if (!refreshPromise) {
      refreshPromise = refreshTokens().finally(() => {
        refreshPromise = null;
      });
    }

    try {
      const newTokens = await refreshPromise;
      storeTokens(newTokens);
      response = await doFetch(newTokens.access_token);
    } catch {
      redirectToLogin();
      throw new Error("Sessão expirada");
    }
  }

  return response;
}

async function refreshTokens() {
  const refreshToken = getStoredRefreshToken();
  const response = await fetch(`${AUTH_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) throw new Error("Refresh falhou");
  return await response.json();
}
```

**Importante sobre rotação:** cada chamada a `/auth/refresh` **revoga o refresh token usado e emite um par novo** (access + refresh). Sempre substitua os dois tokens guardados pelo par retornado — reutilizar o `refresh_token` antigo depois de um refresh bem-sucedido dispara a proteção anti-replay do Auth Service e **revoga todas as sessões do usuário** (ver Seção 7 da especificação técnica do serviço).

---

## 8. Logout

```javascript
async function logout(accessToken, refreshToken) {
  await fetch(`${AUTH_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  clearStoredTokens();
  redirectToLogin();
}
```

Para "sair de todos os dispositivos" (ex: botão de segurança em configurações de conta), use `POST /auth/logout-all` (sem corpo, só o header `Authorization`) — revoga todas as sessões do usuário, não só a atual.

Mesmo que a chamada de rede falhe (usuário sem internet, por exemplo), **sempre limpe os tokens locais e redirecione para o login no cliente** — não deixe o logout do lado do cliente depender de uma resposta de rede bem-sucedida.

---

## 9. Aplicando RBAC no lado do cliente

O Auth Service já aplica RBAC no servidor — sua aplicação **nunca deve confiar apenas na UI** para bloquear ações (esconder um botão não impede uma chamada de API direta). Ainda assim, é comum querer esconder elementos de interface para usuários sem permissão, para uma experiência melhor.

`GET /users/me` retorna o usuário com suas roles (e, dentro de cada role, as permissions):

```json
{
  "id": "...",
  "email": "admin@example.com",
  "roles": [
    {
      "id": "...",
      "name": "admin",
      "permissions": [
        { "code": "user:list", ... },
        { "code": "role:create", ... }
      ]
    }
  ]
}
```

Exemplo de helper no frontend:

```javascript
function hasPermission(user, permissionCode) {
  if (user.is_superuser) return true;
  return user.roles.some((role) =>
    role.permissions.some((permission) => permission.code === permissionCode)
  );
}

// Uso:
if (hasPermission(currentUser, "user:list")) {
  // mostrar o link para a tela de gestão de usuários
}
```

Trate sempre um `403` (`PERMISSION_DENIED`) vindo da API como o sinal definitivo de "sem permissão" — a checagem no cliente é só cosmética.

---

## 10. Dois padrões de integração backend-a-backend

Se sua aplicação tem um backend próprio que precisa saber quem é o usuário autenticado, existem dois padrões:

### Padrão A — Proxy/API Gateway (recomendado para a maioria dos casos)

Seu backend **nunca decodifica o JWT sozinho**. A cada requisição, ele chama `GET /users/me` no Auth Service usando o token recebido do cliente, e confia na resposta.

- ✅ Simples, sempre reflete o estado mais atual (conta desativada, permissões alteradas).
- ⚠️ Uma chamada de rede extra por requisição — considere cache de curta duração (segundos) se o volume for alto.

```python
# Exemplo em Python (qualquer framework)
import httpx

async def get_current_user(authorization_header: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_BASE_URL}/users/me",
            headers={"Authorization": authorization_header},
        )
    if response.status_code != 200:
        raise PermissionError("Não autenticado")
    return response.json()
```

### Padrão B — Validação local do JWT (para alta performance/baixa latência)

Seu backend decodifica e valida a assinatura do JWT **localmente**, sem chamar o Auth Service a cada requisição. Isso exige que seu backend conheça o mesmo `JWT_SECRET_KEY` e `JWT_ALGORITHM` configurados no Auth Service.

- ✅ Sem chamada de rede extra — muito mais rápido.
- ⚠️ Seu backend só sabe o que está *dentro do token* (`sub`, `type`, `exp`, `sid`) — não sabe se a conta foi desativada ou o refresh token revogado *depois* que o access token foi emitido (você aceita esse risco até o token expirar, no máximo `ACCESS_TOKEN_EXPIRE_MINUTES`).
- ⚠️ Compartilhar o `JWT_SECRET_KEY` entre serviços aumenta a superfície de risco — trate como segredo crítico em ambos os lugares.

```python
from jose import jwt, JWTError

def validate_access_token_locally(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise PermissionError("Token inválido ou expirado")
    if payload.get("type") != "access":
        raise PermissionError("Tipo de token incorreto")
    return payload  # contém "sub" (user_id), "sid" (session_id), "exp", etc.
```

Use o Padrão B só se performance for genuinamente crítica — na dúvida, comece pelo Padrão A.

---

## 11. CORS

O Auth Service só aceita requisições de navegador vindas de origens listadas em `CORS_ALLOWED_ORIGINS` (variável de ambiente do Auth Service, não da sua aplicação). Se sua aplicação frontend roda em `https://app.suaempresa.com`, peça para quem administra o Auth Service incluir essa origem:

```dotenv
CORS_ALLOWED_ORIGINS=["https://app.suaempresa.com","http://localhost:3000"]
```

Sem isso, o navegador bloqueia a requisição no preflight (`OPTIONS`) antes mesmo dela chegar ao servidor — isso **não é um bug de rede**, é uma proteção de segurança do próprio navegador.

---

## 12. Checklist de segurança

- [ ] `access_token` nunca é persistido em `localStorage`/`sessionStorage` num SPA público.
- [ ] `refresh_token` fica em cookie `httpOnly` + `Secure` + `SameSite`, ou em armazenamento seguro nativo (mobile).
- [ ] Toda comunicação com o Auth Service usa **HTTPS** em produção (nunca HTTP puro fora de desenvolvimento local).
- [ ] Sua aplicação trata `401` disparando o fluxo de refresh, e `403` como "sem permissão" — não como o mesmo erro genérico.
- [ ] Um botão de "sair de todos os dispositivos" (`/auth/logout-all`) está disponível nas configurações de conta do usuário.
- [ ] Se você usa o Padrão B (validação local de JWT), o `JWT_SECRET_KEY` é tratado como segredo com o mesmo rigor em ambos os serviços (nunca em código-fonte, nunca em log).
- [ ] Você nunca loga o valor de `access_token`/`refresh_token`/senha em nenhum lugar (nem no seu próprio backend).

---

## 13. Erros comuns e como tratá-los

| Código HTTP | `error.code` | O que significa | O que fazer no cliente |
|---|---|---|---|
| 401 | `INVALID_CREDENTIALS` | E-mail ou senha incorretos | Mostrar mensagem genérica (não revele qual campo está errado) |
| 423 | `ACCOUNT_LOCKED` | Conta bloqueada por tentativas de login falhas | Informar o usuário para tentar novamente mais tarde |
| 403 | `ACCOUNT_NOT_VERIFIED` | E-mail ainda não confirmado | Redirecionar para tela de "confirme seu e-mail" |
| 403 | `ACCOUNT_INACTIVE` | Conta desativada por um admin | Informar e sugerir contato com suporte |
| 401 | `TOKEN_EXPIRED` / `TOKEN_INVALID` | Access token expirado/inválido | Disparar fluxo de refresh (seção 7) |
| 401 | `TOKEN_REVOKED` | Refresh token reutilizado após revogação (replay detectado) | Forçar novo login — todas as sessões foram encerradas por segurança |
| 403 | `PERMISSION_DENIED` | Usuário autenticado, mas sem a permissão RBAC exigida | Mostrar "acesso negado", não redirecionar para login |
| 409 | `EMAIL_ALREADY_EXISTS` | Cadastro com e-mail já usado | Sugerir login ou recuperação de senha |
| 429 | `RATE_LIMITED` | Muitas requisições em pouco tempo às rotas de auth | Mostrar mensagem de "tente novamente em instantes", não repetir automaticamente sem backoff |

Todas as respostas de erro seguem o mesmo formato:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "E-mail ou senha incorretos.",
    "details": null
  }
}
```

Trate `error.code` programaticamente (é estável) — `error.message` é para exibição humana e pode mudar de texto sem aviso.
