# scripts/

Scripts operacionais que rodam **fora** do ciclo de requisição HTTP — manutenção, seed de dados, tarefas agendadas (cron/job). Nenhum código aqui é importado pela aplicação (`app/`); é sempre executado manualmente ou por um agendador externo.

## Scripts disponíveis

### `seed_permissions.py`

Cria (de forma idempotente) todas as permissões definidas em `app/core/constants.py::PermissionCode` e uma role `admin` com todas elas atribuídas. Necessário rodar uma vez após a primeira migração, em qualquer ambiente novo — sem isso, o RBAC existe estruturalmente no banco, mas não há nenhuma permissão/role cadastrada para atribuir a ninguém.

```bash
python scripts/seed_permissions.py
```

Ver seção 8 do `README.md` da raiz para o passo a passo completo.

## Convenções para novos scripts

- Cada script deve ser executável isoladamente com `python scripts/nome_do_script.py`, sem depender de estado deixado por outro script.
- Scripts que modificam dados devem ser **idempotentes** (rodar duas vezes não deve duplicar ou corromper dados) sempre que possível.
- Scripts devem usar a mesma configuração do `.env` que a aplicação (via `app.core.config.settings`) — nunca hardcode credenciais ou strings de conexão.
- Scripts que acessam o banco devem gerenciar sua própria sessão/engine e fechá-la explicitamente ao final (ver `seed_permissions.py` como referência).

## Candidatos naturais a próximos scripts

- **Limpeza de refresh tokens expirados**: `RefreshTokenRepository.delete_expired()` (`app/repositories/refresh_token_repository.py`) já existe para isso — falta um script fino que o chame periodicamente (ex: via cron diário), evitando que a tabela `refresh_tokens` cresça indefinidamente com tokens que já não servem para nada.
- **Exportação de logs de auditoria** para um sistema externo (SIEM), se o volume de logs estruturados justificar não depender só do `stdout`.
