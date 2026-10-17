# PROJECT_STATE — oraex-claude-plugins

Canal de contexto entre máquinas e sessões. A skill `oraex-baseline:sessao` lê
este arquivo ao abrir e propõe atualizá-lo ao encerrar. **Sem segredos nem IDs de
conta** — esses ficam na memória do projeto (privada).

## Estado atual

- Marketplace: `ORAEX/oraex-claude-plugins` (repositório público).
- Plugins:
  - **oraex-baseline** — skills `env-conventions`, `mcp-baseline`, `sessao`.
  - **oraex-security** — skills `audit-mfa`, `revisao-seguranca`; agent `oraex-security-review`.
  - **oraex-design** — skill `revisao-design`; agent `oraex-design-review`.
  - **oraex-ui** — skill `revisao-ui`; agent `oraex-ui-review`; baseline de
    identidade visual em `references/identidade-visual.md` + logos em `assets/logo/`.
  - **oraex-plano** — skill `plano-fases`: plano em fases em `docs/<PLANO>.plan.json`
    (fonte da verdade) + quadro em Artifact no mesmo URL, carimbado com o commit;
    `plan.py` (stdlib) valida/renderiza/compara. Exemplo publicado (fictício):
    https://claude.ai/artifact/FDFD6krapf4B22nnW8N8hr
- Agents e skills de revisão (design + segurança de tenant) migrados do
  `~/projects/itsmx/.claude` para o marketplace. Disparo por gatilho/momento
  (não auto-spawn no start da sessão — decisão consciente).
- Padrão de segredo de MCP **validado ponta a ponta**: SSM Parameter Store
  `SecureString` per-dev, ABAC tag-based por `DevId`, permission set dedicado
  (`AWSDeveloperAccess`) com `Deny` que isola. Operacional e IDs concretos: memória.
- Este repo **dogfooda** a `sessao`: `scripts/session.sh` roda validação de plugin
  + guarda de bump de versão.
- **Identidade visual ORAEX** (rebranding 2026, decisão de comitê) codificada no
  `oraex-ui`: azul `#1E74C8`, tipografia Archivo/IBM Plex Sans (Michroma só
  wordmark), tokens em duas camadas (seed sobrescrevível vs semânticos fixos,
  light+dark em `oklch`), pronto p/ white-label multi-tenant — mas o motor de
  tema por tenant é `[ADIADO]` (só a costura existe). Kit de marca original em
  `~/Documents/ORAEX/Marketing/Rebranding 2026/rebranding/`.

## Convenções (fonte da verdade = o baseline)

- `.env` commitado não-secreto; `.env.local` gitignored; segredo no Parameter Store
  puxado via `.envrc`. Ver skill `env-conventions`.
- **Identidade per-dev fora do arquivo versionado**: `ORAEX_DEV_ID` mora no
  `.envrc.local` (gitignored); o `.envrc` só faz `source_env_if_exists .envrc.local`
  e envolve o SSM em `if [ -n "$ORAEX_DEV_ID" ]`. Contrato em `.envrc.local.example`.
  Corrigido na fonte (`env-conventions` v0.4.0); já aplicado no itsmx.
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
- [ ] Propagar o `.envrc.local` per-dev para **crmx** e **finx** (fonte já corrigida).
- [ ] finx: aplicar os tokens ORAEX em `app/globals.css` (hoje é o tema shadcn
      cinza de fábrica) — patch pronto para preparar quando pedir.
- [ ] finx: rodar `revisao-ui` numa tela real e fechar o gap que ela apontar.

## Como retomar

- Abrir: "bom dia" / "vamos retomar" → skill `sessao` → `./scripts/session.sh start`.
- Encerrar: "encerrando" → `./scripts/session.sh end` (valida + guarda de bump).
