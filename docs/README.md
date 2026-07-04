# docs/

Esta pasta é reservada para documentação **estendida** do projeto — conteúdo que não cabe (ou polui) o `README.md` da raiz, mas que uma equipe mantendo este serviço em produção provavelmente vai precisar eventualmente.

## Documentos disponíveis

- **[`integration-guide.md`](./integration-guide.md)** — como uma aplicação cliente (frontend, backend, ou ambos) deve se integrar ao Auth Service: fluxos de login/registro/MFA, onde guardar tokens, renovação automática, RBAC no cliente, padrões de integração backend-a-backend, CORS, e uma tabela de erros comuns.
- **[`deployment-guide.md`](./deployment-guide.md)** — como subir a aplicação, o PostgreSQL e o Redis em produção: diferenças entre dev e produção, opções de banco/Redis gerenciados vs. self-hosted, build e réplicas da aplicação, migrações no fluxo de deploy, VPS com Docker Compose vs. PaaS, HTTPS, observabilidade e checklists de segurança/deploy.
- **[`usage-guide.md`](./usage-guide.md)** — o que a API faz do ponto de vista funcional: tipos de usuário, ciclo de vida da conta, fluxos completos (cadastro, login, MFA, recuperação de senha), como o RBAC funciona na prática, fluxo de administrador (criar roles/permissões, promover um usuário), gestão de sessões, e uma tabela de todos os endpoints com a permissão exigida por cada um.

## O que mais colocar aqui, conforme o projeto cresce

Candidatos naturais a próximos documentos:

- **`architecture/`** — diagramas de arquitetura (C4, sequência dos fluxos de autenticação, etc.), se o projeto crescer a ponto de precisar deles além do diagrama textual já presente na especificação original.
- **`adr/`** — *Architecture Decision Records*: um arquivo Markdown por decisão arquitetural relevante (ex: "por que JWT em vez de sessão opaca", "por que RBAC simples sem hierarquia de roles"). O `README.md` da raiz já lista as decisões tomadas durante a geração inicial deste projeto (seção "Decisões de implementação") — ADRs formais valem a pena a partir do momento em que decisões *futuras* precisarem desse nível de registro individual.
- **`postman/`** ou **`insomnia/`** — coleções exportadas para testar a API manualmente, como alternativa ao Swagger UI (`/docs`).
- **`runbooks/`** — procedimentos operacionais para incidentes comuns (ex: "como rotacionar o `JWT_SECRET_KEY` sem derrubar sessões ativas", "como identificar um ataque de credential stuffing nos logs de auditoria").

Se você é a próxima pessoa adicionando algo aqui, crie a subpasta correspondente e um `README.md` dentro dela explicando o que é.
