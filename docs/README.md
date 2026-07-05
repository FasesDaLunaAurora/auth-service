# docs/

Documentação estendida do projeto — cada guia é escrito para um público diferente, então comece pelo que corresponde ao que você está tentando fazer:

| Documento | Para quem / quando usar |
|---|---|
| [`SPEC.md`](./SPEC.md) | Especificação técnica completa — arquitetura, modelagem de dados, contrato de endpoints. Ponto de partida para entender o projeto por inteiro. |
| [`development-guide.md`](./development-guide.md) | Rodar e desenvolver o projeto localmente: pré-requisitos (Docker Desktop, Docker Engine ou Podman), configuração, testes, migrações, qualidade de código e troubleshooting. |
| [`deployment-guide.md`](./deployment-guide.md) | Colocar o serviço em produção: PostgreSQL e Redis (gerenciados ou self-hosted), build da imagem, migrações no fluxo de deploy, VPS vs. PaaS, HTTPS, observabilidade. |
| [`integration-guide.md`](./integration-guide.md) | Integrar outra aplicação (frontend ou backend) a este serviço: fluxos de login/MFA, onde guardar tokens, renovação automática, RBAC no cliente, erros comuns. |
| [`usage-guide.md`](./usage-guide.md) | O que a API faz do ponto de vista funcional: tipos de usuário, ciclo de vida da conta, fluxos completos, RBAC na prática, tabela de endpoints. |
| [`permissions-reference.md`](./permissions-reference.md) | Dicionário detalhado de cada permissão do RBAC: o que libera, nível de risco, combinações perigosas, exemplos de roles por função. |

## Convenções para novos documentos

- Um guia por público/objetivo — evite misturar "como rodar localmente" com "como fazer deploy" no mesmo arquivo.
- Prefira exemplos de comando reais (copiáveis) a descrições abstratas.
- Se um documento ficar desatualizado em relação ao código, corrija-o no mesmo PR que muda o comportamento — documentação errada é pior que documentação ausente.

## Candidatos a próximos documentos

- **`adr/`** — *Architecture Decision Records* individuais, se decisões futuras precisarem de registro mais formal do que uma linha na lista de decisões do `development-guide.md`.
- **`postman/`** ou **`insomnia/`** — coleções para testar a API manualmente, como alternativa ao Swagger UI (`/docs`).
- **`runbooks/`** — procedimentos para incidentes comuns (rotacionar `JWT_SECRET_KEY` sem derrubar sessões ativas, identificar um ataque de credential stuffing nos logs de auditoria, etc.).
