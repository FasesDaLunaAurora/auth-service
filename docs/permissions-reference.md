# Referência de Roles e Permissões (RBAC)

Este documento é a referência detalhada de **cada permissão que existe no sistema**: o que ela libera, qual endpoint ela guarda, e o nível de risco de atribuí-la a alguém. Para uma visão geral de como RBAC funciona (o modelo usuário → role → permission), veja `docs/usage-guide.md`, seção 4 — este documento aqui é o "dicionário" detalhado, aquele é a explicação do mecanismo.

---

## Sumário

- [1. Como ler este documento](#1-como-ler-este-documento)
- [2. Permissões de usuário (`user:*`)](#2-permissões-de-usuário-user)
- [3. Permissões de role (`role:*`)](#3-permissões-de-role-role)
- [4. Permissões de permissão (`permission:*`)](#4-permissões-de-permissão-permission)
- [5. Permissões de sessão (`session:*`) — reservadas](#5-permissões-de-sessão-session--reservadas)
- [6. `is_superuser`: o atalho que ignora tudo isso](#6-is_superuser-o-atalho-que-ignora-tudo-isso)
- [7. A role `admin` pré-criada](#7-a-role-admin-pré-criada)
- [8. Combinações perigosas — leia antes de montar uma role nova](#8-combinações-perigosas--leia-antes-de-montar-uma-role-nova)
- [9. Exemplos de roles por função (least privilege)](#9-exemplos-de-roles-por-função-least-privilege)

---

## 1. Como ler este documento

Cada permissão tem uma classificação de risco:

| Nível | Significado |
|---|---|
| Baixo | Só leitura, ou ação sobre o próprio impacto é limitado |
| Médio | Modifica dados, mas de forma reversível e auditável |
| Alto | Ação destrutiva (exclusão) ou que afeta múltiplos usuários |
| Crítico | Pode levar a escalonamento de privilégio — quem tem essa permissão pode, na prática, conceder poderes a si mesmo ou a terceiros |

**Regra prática:** permissões de nível Crítico nunca devem ir para uma role que não seja a de administração plena. Dar uma permissão crítica "só um pouquinho" (ex: "confio nessa pessoa, mas só pra esse caso") não existe no modelo atual — ela vale igual pra qualquer uso do endpoint.

---

## 2. Permissões de usuário (`user:*`)

### `user:list` — Risco: Baixo
- **Libera:** `GET /users` — listar todos os usuários cadastrados, com busca e paginação.
- **Por quê é baixo risco:** exposição de dados (e-mail, nome, status da conta) de todos os usuários, mas nenhuma ação destrutiva.
- **Bom para:** qualquer função que precise localizar clientes/funcionários no sistema (atendimento, suporte).

### `user:read` — Risco: Baixo
- **Libera:** `GET /users/{id}` — ver o detalhe de um usuário específico (perfil, roles atribuídas, status).
- **Observação:** baixo risco isolado, mas combinado com `user:list` dá visão completa da base de usuários.
- **Bom para:** mesmas funções que `user:list` — normalmente as duas andam juntas.

### `user:update` — Risco: Médio
- **Libera:** `PATCH /users/{id}` (editar nome/status), `POST /users/{id}/activate`, `POST /users/{id}/deactivate`.
- **Por quê é médio risco:** desativar a conta de alguém é reversível (outro admin reativa), mas é uma ação que impacta o acesso de terceiros imediatamente.
- **Não libera:** troca de senha ou e-mail de outro usuário — isso não existe como ação administrativa no sistema hoje (só o próprio usuário troca a própria senha).

### `user:delete` — Risco: Alto
- **Libera:** `DELETE /users/{id}` — exclusão lógica (soft delete) de um usuário.
- **Por quê é alto risco:** embora seja "lógica" (o registro continua no banco para auditoria), a API passa a tratar o usuário como inexistente — login, tokens e sessões dele param de funcionar imediatamente, e não há endpoint de "desfazer exclusão" hoje (precisaria ser feito direto no banco).
- **Cuidado:** não dê essa permissão junto com `user:update` para alguém que só precisa de funções de suporte básico — as duas juntas dão controle total sobre a conta de qualquer pessoa.

---

## 3. Permissões de role (`role:*`)

### `role:list` — Risco: Baixo / `role:read` — Risco: Baixo
- **Libera:** `GET /roles` e `GET /roles/{id}` — ver quais roles existem e quais permissões cada uma tem.
- **Observação:** é só leitura, mas revela a estrutura inteira de permissões do sistema. Ainda assim, geralmente inofensivo.

### `role:create` — Risco: Médio
- **Libera:** `POST /roles` — criar uma role nova (vazia, sem permissões ainda).
- **Observação:** médio risco sozinho (uma role vazia não faz nada), mas veja a seção 8 — combinado com `permission:assign`, vira crítico.

### `role:update` — Risco: Médio
- **Libera:** `PATCH /roles/{id}` — renomear ou mudar a descrição de uma role existente.
- **Observação:** não muda quais permissões a role tem, só metadados.

### `role:delete` — Risco: Alto
- **Libera:** `DELETE /roles/{id}` — exclui a role permanentemente (exclusão física, não lógica — diferente de usuário).
- **Por quê é alto risco:** todo usuário que tinha essa role perde as permissões associadas a ela imediatamente, sem aviso prévio a esses usuários.

### `role:assign` — Risco: CRÍTICO
- **Libera:** `POST /users/{user_id}/roles` e `DELETE /users/{user_id}/roles/{role_id}` — atribuir ou remover **qualquer** role de **qualquer** usuário.
- **Por quê é crítico:** quem tem essa permissão pode atribuir a role `admin` (ou qualquer role com `permission:assign` + `role:assign`) a si mesmo ou a qualquer outra conta. **Na prática, ter `role:assign` é equivalente a poder se tornar administrador completo a qualquer momento**, mesmo que a role atual da pessoa não tenha nenhuma outra permissão.
- **Regra de ouro:** só dê `role:assign` para quem você já trataria como administrador pleno. Não existe hoje um jeito de restringir "pode atribuir *essas* roles, mas não *aquelas*" — é tudo ou nada.

---

## 4. Permissões de permissão (`permission:*`)

### `permission:list` — Risco: Baixo
- **Libera:** `GET /permissions` — listar todas as permissões que existem no sistema.

### `permission:create` — Risco: Médio
- **Libera:** `POST /permissions` — criar uma permissão nova (ex: `order:approve` para um projeto futuro).
- **Observação:** médio risco sozinho — criar uma permissão não atribui ela a ninguém.

### `permission:update` — Risco: Baixo
- **Libera:** `PATCH /permissions/{id}` — só edita a descrição da permissão, não o código nem a quem ela está atribuída.

### `permission:delete` — Risco: Alto
- **Libera:** `DELETE /permissions/{id}` — remove a permissão do sistema inteiro, tirando-a de toda role que a tinha.
- **Por quê é alto risco:** pode revogar acesso de várias roles/usuários de uma vez, sem aviso.

### `permission:assign` — Risco: CRÍTICO
- **Libera:** `POST /roles/{role_id}/permissions` e `DELETE /roles/{role_id}/permissions/{permission_id}` — atribuir ou remover qualquer permissão de qualquer role.
- **Por quê é crítico:** mesmo motivo que `role:assign` — quem tem essa permissão pode dar `role:assign` e `permission:assign` para uma role que ele próprio tem, fechando o ciclo de auto-promoção a administrador pleno.
- **Regra de ouro:** mesma da seção anterior — trate como equivalente a admin completo.

---

## 5. Permissões de sessão (`session:*`) — reservadas

`session:list` e `session:revoke` existem como constantes no código (`app/core/constants.py::PermissionCode`), mas **nenhum endpoint atual as utiliza** — a gestão de sessão hoje é feita só pelo próprio dono (`GET /sessions`, `DELETE /sessions/{id}`), sem endpoint administrativo equivalente (ex: "um admin forçar logout de outro usuário" não existe ainda).

Se seu caso de uso precisar disso (ex: suporte precisar encerrar a sessão de um cliente a pedido dele por telefone), é uma extensão razoável a ser construída — as permissões já reservadas facilitam isso.

---

## 6. `is_superuser`: o atalho que ignora tudo isso

Todo usuário tem um campo `is_superuser` (`true`/`false`). Quando `true`:
- **Todas** as checagens de permissão acima são puladas — o código nem chega a olhar as roles do usuário (`RoleService.user_has_permission` retorna `True` direto, ver `app/services/role_service.py`).
- Não existe um "superuser parcial" — é tudo ou nada, assim como `role:assign`/`permission:assign`, mas ainda mais direto (nem precisa de uma role pra isso).

**Quando usar `is_superuser` em vez de montar uma role admin via RBAC:**
- Pra a primeira conta administrativa do sistema (quando ainda não existe nenhuma role criada) — é o único jeito de "começar", já que só quem já tem `role:assign` consegue atribuir roles, e ninguém tem isso ainda no primeiro usuário.
- Fora desse caso inicial, prefira RBAC (role `admin` com as permissões, seção 7) em vez de `is_superuser` — fica mais fácil de auditar quem tem o quê, e permite no futuro criar administradores "parciais" se precisar.

---

## 7. A role `admin` pré-criada

O script `scripts/seed_permissions.py` cria automaticamente uma role chamada **`admin`** com **todas** as permissões listadas neste documento atribuídas a ela — incluindo as críticas.

Isso significa: atribuir a role `admin` a alguém é **equivalente** a marcar `is_superuser=True` nela, na prática — a única diferença é que fica registrado via RBAC (mais fácil de revisar "quem tem essa role" do que "quem tem essa flag", já que a role aparece em `GET /users/{id}`).

---

## 8. Combinações perigosas — leia antes de montar uma role nova

| Combinação | Por que é perigosa |
|---|---|
| `role:assign` sozinha | Já é crítica sozinha — ver seção 3. |
| `permission:assign` sozinha | Já é crítica sozinha — ver seção 4. |
| `role:create` + `permission:assign` | Alguém pode criar uma role nova, encher ela de permissões (incluindo `role:assign`), e se atribuir essa role — mesmo sem ter `role:assign` diretamente no início. |
| `user:update` + `role:assign` | Controle total sobre contas de terceiros: pode desativar/reativar **e** trocar as permissões de qualquer um. |

**A defesa prática contra tudo isso:** trate `role:assign` e `permission:assign` como um par indivisível — só dê as duas juntas, só para quem é de fato administrador pleno, e nunca como parte de uma role "intermediária".

---

## 9. Exemplos de roles por função (least privilege)

Sugestões de composição, pensando no princípio de **dar só o necessário**:

### "Atendimento" — vê clientes, não modifica nada
```
user:list
user:read
```

### "Suporte" — vê clientes e pode desativar conta em caso de fraude reportada
```
user:list
user:read
user:update
```
*(sem `user:delete` — exclusão fica reservada a alguém mais sênior)*

### "Gestor de acesso" — pode organizar roles, mas não criar administradores novos
```
role:list
role:read
role:create
role:update
permission:list
```
*(deliberadamente SEM `role:assign` nem `permission:assign` — esse "gestor" pode preparar roles, mas alguém com privilégio maior precisa efetivamente atribuí-las a pessoas ou anexar as permissões críticas)*

### "Administrador pleno" — a role `admin` já criada pelo seed
```
todas as permissões, incluindo role:assign e permission:assign
```

Não existe hoje um meio-termo automático entre "Gestor de acesso" e "Administrador pleno" — esse é exatamente o motivo de `role:assign`/`permission:assign` serem tratadas à parte: qualquer role que as tenha *é*, na prática, administração plena, não importa o nome que você dê a ela.
