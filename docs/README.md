# docs/

Esta pasta é reservada para documentação **estendida** do projeto — conteúdo que não cabe (ou polui) o `README.md` da raiz, mas que uma equipe mantendo este serviço em produção provavelmente vai precisar eventualmente.

Ela começa vazia de propósito: gerar documentação especulativa antes de existirem decisões reais para documentar tende a ficar desatualizado rápido e a confundir mais do que ajudar. O que colocar aqui, conforme o projeto evolui:

- **`architecture/`** — diagramas de arquitetura (C4, sequência dos fluxos de autenticação, etc.), se o projeto crescer a ponto de precisar deles além do diagrama textual já presente na especificação original.
- **`adr/`** — *Architecture Decision Records*: um arquivo Markdown por decisão arquitetural relevante (ex: "por que JWT em vez de sessão opaca", "por que RBAC simples sem hierarquia de roles"). O `README.md` da raiz já lista as decisões tomadas durante a geração inicial deste projeto (seção "Decisões de implementação") — ADRs formais valem a pena a partir do momento em que decisões *futuras* precisarem desse nível de registro individual.
- **`postman/`** ou **`insomnia/`** — coleções exportadas para testar a API manualmente, como alternativa ao Swagger UI (`/docs`).
- **`runbooks/`** — procedimentos operacionais para incidentes comuns (ex: "como rotacionar o `JWT_SECRET_KEY` sem derrubar sessões ativas", "como identificar um ataque de credential stuffing nos logs de auditoria").

Se você é a primeira pessoa adicionando algo aqui, crie a subpasta correspondente e um `README.md` dentro dela explicando o que é.
