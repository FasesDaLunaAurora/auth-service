# Roadmap Técnico — infraestrutura pronta, funcionalidade não conectada

Este documento existe para mapear partes do código que já têm a **infraestrutura construída** (uma classe, um método, um campo no banco), mas que ainda não estão **conectadas** a nenhum endpoint ou automação, ou seja, não aparecem em nenhum outro guia porque, tecnicamente, "não fazem nada" hoje.

A ideia é documentar **o que já existe de base**, **o que falta** para funcionar de ponta a ponta, e **como** implementar quando a necessidade aparecer de verdade, evitando reinventar a decisão de design na hora.

---

## Sumário

- [1. Login social (OAuth2)](#1-login-social-oauth2)
- [2. Gestão administrativa de sessões](#2-gestão-administrativa-de-sessões)
- [3. Limpeza automática de refresh tokens expirados](#3-limpeza-automática-de-refresh-tokens-expirados)
- [4. Limitações conhecidas (não são lacunas, são decisões)](#4-limitações-conhecidas-não-são-lacunas-são-decisões)
- [5. Convenção para adicionar algo novo aqui](#5-convenção-para-adicionar-algo-novo-aqui)

---

## 1. Login social (OAuth2)

### O que já existe

`app/security/oauth2_handler.py` implementa o **mecanismo genérico** do fluxo Authorization Code (RFC 6749), independente de provedor:

- `OAuth2ProviderConfig` — dataclass com os campos que qualquer provedor precisa (`client_id`, `client_secret`, URLs de autorização/token/userinfo, `redirect_uri`, `scopes`).
- `OAuth2Handler.generate_state()` — gera o token anti-CSRF do fluxo OAuth2.
- `OAuth2Handler.build_authorization_url()` — monta a URL de redirecionamento para a tela de consentimento do provedor.
- `OAuth2Handler.exchange_code_for_token()` — troca o `authorization_code` do callback por um access token do provedor.
- `OAuth2Handler.fetch_user_info()` — busca e-mail/nome do usuário no provedor, usando o access token.

A pasta `app/integrations/oauth_providers/` existe e está vazia de propósito — é onde entrariam as configurações concretas de cada provedor.

### O que falta

1. **Um arquivo de configuração por provedor**, por exemplo:

```python
# app/integrations/oauth_providers/google.py
from app.security.oauth2_handler import OAuth2ProviderConfig
from app.core.config import settings

google_provider = OAuth2ProviderConfig(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
    redirect_uri=settings.GOOGLE_REDIRECT_URI,
    scopes=["openid", "email", "profile"],
)
```

Isso exige adicionar as variáveis correspondentes (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`) em `app/core/config.py` e no `.env.example`.

2. **Duas rotas novas**, hoje inexistentes em `app/api/routes/auth_routes.py`:

| Rota (sugerida) | Descrição |
|---|---|
| `GET /auth/oauth/{provider}/authorize` | Gera o `state`, guarda em Redis com TTL curto (ex: 5 min), redireciona para `OAuth2Handler.build_authorization_url()` |
| `GET /auth/oauth/{provider}/callback` | Recebe `code` + `state`, valida o `state` contra o que está no Redis (proteção CSRF), troca o código por token, busca e-mail do usuário, cria a conta (se não existir) ou faz login na existente, emite os tokens do próprio Auth Service |

3. **Um método novo em `AuthService`** (ex: `login_with_oauth_provider`) que decide: se já existe um `User` com esse e-mail, loga nele; se não existe, cria um novo (provavelmente já `is_verified=True`, já que o provedor OAuth já confirmou o e-mail — decisão a se tomar na hora de implementar).

### Considerações de segurança a resolver na implementação

- **Validação do `state`** sem isso, o fluxo fica vulnerável a ataque CSRF: um atacante inicia o login OAuth na própria conta, intercepta o link de callback antes de completá-lo, e manda esse link pra vítima. Se ela clicar e o sistema não checar o `state`, ela termina logada na conta do atacante sem perceber e qualquer dado que ela informe ali (cartão, endereço) vaza pra ele. O `state` só existe pra garantir que o `code` recebido no callback pertence à mesma sessão que iniciou o fluxo, não a outra pessoa.
- **Vincular conta existente vs. criar nova**: se um e-mail já tem conta com senha normal e a mesma pessoa tenta "Entrar com Google" usando esse e-mail, logar automaticamente pode ser arriscado — o sistema estaria confiando cegamente que o provedor OAuth verificou a posse real daquele e-mail. Mais seguro: pedir uma confirmação extra nesse caso (senha atual, ou e-mail perguntando "foi você?") em vez de vincular as contas silenciosamente.
- **Registrar qual provider originou a conta**: `User.hashed_password` é obrigatório no schema atual — uma conta criada só via OAuth não teria senha própria, o que quebra o fluxo normal de login e o de "esqueci minha senha". Precisa de um campo tipo `auth_provider` (`null` = senha normal, `"google"` = só via Google) pra a UI saber mostrar a tela certa em vez de um campo de senha que não faz sentido pra esse usuário.

---

## 2. Gestão administrativa de sessões

### O que já existe

- Modelo `Session`, repositório `SessionRepository` com `list_active_for_user`, `revoke`, `revoke_all_for_user`.
- Endpoints **self-service**: `GET /sessions` e `DELETE /sessions/{id}` — cada usuário só vê/revoga as próprias sessões.
- Duas permissões já reservadas em `app/core/constants.py::PermissionCode`: `session:list` e `session:revoke` — definidas, mas **nenhuma rota as utiliza hoje**.

### O que falta

Um caso de uso comum que essas permissões prevêem: suporte ou administrador encerrar a sessão de **outro** usuário — por exemplo, a pedido de um cliente por telefone ("acho que esqueci logado no computador de um cybercafé"), ou como resposta a uma suspeita de conta comprometida.

Rotas sugeridas (não existem hoje):

| Rota (sugerida) | Permissão | Descrição |
|---|---|---|
| `GET /users/{user_id}/sessions` | `session:list` | Lista as sessões ativas de um usuário específico |
| `DELETE /users/{user_id}/sessions/{session_id}` | `session:revoke` | Revoga uma sessão específica de outro usuário |

Implementação é direta: `SessionService` já tem toda a lógica de revogação — só falta um método que não exija que `user_id == session.user_id` (diferente do `revoke_session` atual, que é deliberadamente restrito ao dono, ver `docs/usage-guide.md`, seção 6) mais as duas rotas acima, com a permissão correta no lugar do `CurrentUser` usado hoje.

---

## 3. Limpeza automática de refresh tokens expirados

### O que já existe

`RefreshTokenRepository.delete_expired(older_than: datetime)` (`app/repositories/refresh_token_repository.py`) — um `DELETE` parametrizado, pronto para uso, que remove fisicamente refresh tokens expirados há mais de um certo tempo.

### O que falta

Nenhum script ou automação chama esse método — ele existe, mas nunca é executado. Isso não é um problema de segurança (um refresh token expirado já é rejeitado pela verificação de assinatura/`exp` do JWT antes mesmo de tocar o banco — ver `docs/development-guide.md`, decisão de design nº 6), é só acúmulo de linhas na tabela `refresh_tokens` ao longo do tempo, sem limpeza.

Implementação sugerida: um script fino, no mesmo padrão de `scripts/seed_permissions.py`:

```python
# scripts/cleanup_expired_tokens.py (não existe ainda)
# Chamaria RefreshTokenRepository.delete_expired(older_than=...) com uma
# folga de alguns dias (não a data exata de expiração), para manter uma
# janela forense curta antes de apagar de vez.
```

Agendamento sugerido: cron diário no host (mesmo padrão dos comandos de `docker compose run --rm migrate` já documentados em `docs/deployment-guide.md`), não um scheduler dentro da própria aplicação — evita duplicar a limpeza se um dia houver múltiplas réplicas do serviço rodando ao mesmo tempo.

---

## 4. Limitações conhecidas (não são lacunas, são decisões)

Diferente das seções acima, os itens abaixo não têm "o que falta", são características do design atual, documentadas aqui para quem for avaliar se elas ainda fazem sentido conforme o projeto cresce:

- **RBAC sem hierarquia de roles.** Não existe "role pai/filha" nem herança de permissões entre roles — cada role tem sua lista própria e plana de permissões. Ver `docs/permissions-reference.md` para o modelo completo.
- **Sem confirmação em duas etapas para atribuir permissões críticas** (`role:assign`/`permission:assign`). Quem tem essas permissões pode escalar privilégio imediatamente, sem um segundo aprovador — ver `docs/permissions-reference.md`, seção 8.
- **E-mails em texto puro**, sem template HTML, funcional, mas não é o que se mandaria para um cliente final de uma loja sem antes estilizar.

---

## 5. Convenção para adicionar algo novo aqui

Um item entra neste documento quando: existe código real no repositório (não uma ideia) que **não é alcançável por nenhuma rota ou automação hoje**. Ao implementar um desses itens, mova a seção correspondente daqui para o guia certo (`usage-guide.md` se for uma funcionalidade de produto, `permissions-reference.md` se envolver uma permissão nova, etc.) e apague-a deste documento — este arquivo é sobre o que **ainda não está pronto**, não um histórico do que já foi feito.
