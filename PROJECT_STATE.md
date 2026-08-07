# PROJECT_STATE — oraex-claude-plugins

Canal de contexto entre máquinas e sessões. A skill `oraex-baseline:sessao` lê
este arquivo ao abrir e propõe atualizá-lo ao encerrar. **Sem segredos nem IDs de
conta** — esses ficam na memória do projeto (privada).

## Estado atual

- Marketplace: `ORAEX/oraex-claude-plugins` (repositório público).
- Plugins:
  - **oraex-baseline** — skills `env-conventions`, `mcp-baseline`, `sessao`.
  - **oraex-security** — skill `audit-mfa`.
- Padrão de segredo de MCP **validado ponta a ponta**: SSM Parameter Store
  `SecureString` per-dev, ABAC tag-based por `DevId`, permission set dedicado
  (`AWSDeveloperAccess`) com `Deny` que isola. Operacional e IDs concretos: memória.
- Este repo **dogfooda** a `sessao`: `scripts/session.sh` roda validação de plugin
  + guarda de bump de versão.

## Convenções (fonte da verdade = o baseline)

- `.env` commitado não-secreto; `.env.local` gitignored; segredo no Parameter Store
  puxado via `.envrc`. Ver skill `env-conventions`.
- `.mcp.json` por projeto; Supabase local/SaaS por ambiente (`supabase-<env>`);
  MCP de nuvem opt-in por sessão via `/mcp`. Ver skill `mcp-baseline`.
- **Todo edit de conteúdo de plugin exige bump da `version`** no `plugin.json`,
  senão o cache extraído não re-extrai. Propagar: `marketplace update` → `/reload-plugins`.

## Backlog

- [ ] Hook de pre-commit que barra commit em `plugins/*` sem bump de `version`.
- [ ] Seção "migrar projeto existente" no `env-conventions`.
- [ ] Guardrail do `ssm:PutParameter` (dev só tagueia o próprio `DevId`).
- [ ] IaC (CloudFormation/CDK) do permission set + grupo `Developers`.
- [ ] Trocar assignment do usuário pelo grupo `Developers` (onboarding oficial).
- [ ] itsmx: confirmar migração concluída ao padrão do baseline.

## Como retomar

- Abrir: "bom dia" / "vamos retomar" → skill `sessao` → `./scripts/session.sh start`.
- Encerrar: "encerrando" → `./scripts/session.sh end` (valida + guarda de bump).
