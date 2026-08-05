---
name: mcp-baseline
description: Configura os MCP servers de um projeto no padrão ORAEX — escrevendo um .mcp.json local (escopo de projeto) com Supabase, GitHub e AWS. Prefere OAuth quando o servidor oferece; para servidores que só aceitam token, usa segredo per-dev (Secrets Manager via SSO), nunca literal no arquivo. Use quando o usuário pedir para configurar/adicionar MCP num projeto, ligar Supabase/GitHub/AWS MCP, padronizar .mcp.json, ou tratar segredos de MCP por desenvolvedor.
---

# Baseline de MCP por projeto (padrão ORAEX)

Escreve o `.mcp.json` **do projeto atual** no padrão da ORAEX. A configuração é
**local, por projeto** — cada repo tem o seu Supabase, seu escopo de GitHub — e
nenhum segredo entra no arquivo nem no contexto.

Pré-requisitos: sessão SSO ativa (`aws sso login`) para os MCPs que dependem de
AWS; e o plugin **`aws-core`** ligado se você for usar `asm-exec`/AWS MCP.

## Por que `.mcp.json` de projeto, e não do plugin

Um `.mcp.json` empacotado no plugin é **global**: subiria em todo projeto. Não
serve, porque cada projeto aponta para um Supabase diferente. Então o padrão
mora aqui como **gerador**, e o arquivo nasce no repo, escopo de projeto.

`.mcp.json` é versionado (entra no git): ele **não contém segredo**, só
referências. Precedência no Claude Code: `local` > **`.mcp.json` do projeto** >
`user` > plugin. Este arquivo vence o baseline; cada dev ainda pode sobrescrever
em `local`.

## Regra de autenticação

**OAuth quando o servidor oferece; token per-dev só para quem exige.** OAuth
resolve identidade por dev sem segredo para guardar — é sempre a primeira opção.
Só cai para token quando o servidor não suporta OAuth.

## Os MCPs iniciais (mecanismo verificado)

| MCP | Transporte | Auth | Per-projeto |
|---|---|---|---|
| **Supabase** | um server **por ambiente**: local (`localhost:<porta>/mcp`) e/ou SaaS (`mcp.supabase.com/mcp`) | local: **nenhuma** · SaaS: **OAuth** no navegador | um `supabase-<env>` por ambiente; porta local de `config.toml`, `project_ref` por SaaS |
| **GitHub** | HTTP remoto (`api.githubcopilot.com/mcp/`) | **PAT** em `Authorization: Bearer ${GITHUB_PAT}` | escopo do próprio PAT |
| **AWS** | via plugin `aws-core` | sessão **SSO** (sem segredo) | perfil SSO do ambiente |

- **Supabase:** o nº de ambientes **varia por projeto** (só `local`; ou `local + test + prd`).
  Um `supabase-<env>` por ambiente — ver a seção abaixo. Local é primeira classe.
- **GitHub:** `${GITHUB_PAT}` é expandido **no launch** a partir do ambiente. O
  PAT vem do `.env.local`/`.envrc` — de preferência puxado do Secrets Manager
  (`oraex/dev/<id>/mcp/github`) pela skill [[env-conventions]], não de arquivo estático.
- **AWS:** não duplique — **ligue o `aws-core`**, que já fornece o MCP de AWS
  usando a sessão SSO. Um MCP de AWS próprio no `.mcp.json` só se o projeto exigir.

## Supabase: um server por ambiente (N variável por projeto)

O número de ambientes **varia**: um projeto tem só `local`; outro, sendo
produtivo e de uso massivo, tem `local + test + prd` (test SaaS de verdade). O
padrão é **um MCP server nomeado por ambiente** — `supabase-<env>` — cada um com
o transporte certo para onde aquele ambiente vive. Todos coexistem no mesmo
`.mcp.json`.

**Ambiente local (stack da Supabase CLI)** — sem OAuth, sem segredo. A porta
**não é fixa**: leia de `supabase/config.toml` (`[api] port`), com fallback
54321. Nunca crave a porta — projetos remapeiam (ex.: um CLAUDE.md que usa 57321).

```json
"supabase-local": { "type": "http", "url": "http://localhost:<API_PORT>/mcp" }
```

**Ambiente SaaS (test, prd, staging…)** — OAuth no navegador (PAT não é mais
necessário). `project_ref` escopa ao projeto; `read_only=true` por padrão em
prd/test, `false` só com pedido explícito.

```json
"supabase-prd":  { "type": "http", "url": "https://mcp.supabase.com/mcp?project_ref=<PRD_REF>&read_only=true" },
"supabase-test": { "type": "http", "url": "https://mcp.supabase.com/mcp?project_ref=<TEST_REF>&read_only=true" }
```

**Self-hosted só-token** (raro) — `asm-exec` + Secrets Manager per-dev
(`reference/aws-setup.md`), nunca token literal.

Regras de nome e escopo:

- Nome = `supabase-<env>` com o nome real do ambiente (local, dev, test, staging, prd).
- `read_only=true` em qualquer ambiente produtivo/compartilhado; só o local
  costuma ser leitura+escrita.
- **Descubra quais ambientes o projeto tem — não presuma o número.** Pergunte
  quais existem e o `project_ref` de cada SaaS.

## Taxonomia (decida cada valor por ela)

| Tipo | Exemplo | Como entra |
|---|---|---|
| **OAuth** | Supabase | nada no arquivo além da URL; login no navegador |
| **Segredo per-dev** | PAT do GitHub | `${GITHUB_PAT}` (env) — puxado do Secrets Manager; **nunca** literal |
| **Não-segredo per-projeto** | `project_ref`, owner/repo | literal no `.mcp.json` |
| **Identidade per-máquina** | `ORAEX_DEV_ID`, `AWS_PROFILE`, `GITHUB_PAT` | vem do `.envrc`/`.env.local` (expande no launch) |

Para servidores **stdio** que só aceitam token (fora dos três acima), o padrão é
`asm-exec` + `{{resolve:secretsmanager:oraex/dev/${ORAEX_DEV_ID}/mcp/<servidor>:...}}`,
resolvido em runtime — ver `reference/aws-setup.md`.

## Procedimento

1. Confirme pré-requisitos: `.envrc` com `ORAEX_DEV_ID` (skill [[env-conventions]]);
   `aws sso login` feito; `GITHUB_PAT` no ambiente se for usar GitHub.
2. **Levante os ambientes de Supabase do projeto** (pode ser 1, 2 ou 3+: local,
   test, prd…). Para cada um:
   - **local** → leia a porta de `supabase/config.toml` (`[api] port`, fallback 54321);
   - **SaaS** → colete o `project_ref` e defina `read_only` (true em prd/test, salvo pedido).
   **Pergunte** quais ambientes existem se não estiver claro — não presuma o número.
3. Use `templates/mcp.json` como base e emita **um `supabase-<env>` por ambiente**
   com a URL certa; preencha os demais literais e escreva em `.mcp.json` na raiz.
   **Não** invente `project_ref`, porta nem a quantidade de ambientes.
4. Lembre o usuário: `aws sso login`; para GitHub, ter `GITHUB_PAT` no ambiente
   (idealmente via Secrets Manager — ver [[env-conventions]] e `reference/aws-setup.md`).
5. Valide: `/mcp` na sessão (ou `claude mcp list`). Cada `supabase-<env>` **local**
   conecta direto se o stack estiver de pé (`supabase start`); cada **SaaS** pede
   login OAuth no navegador na primeira vez. `! Needs authentication` costuma ser
   esse OAuth pendente ou sessão SSO expirada.

> **Pacotes/endpoints de MCP mudam.** Antes de gravar, confirme o transporte e a
> URL atuais de cada servidor — este arquivo reflete o estado verificado na data
> da última edição, não uma verdade permanente.

## Regras

- **Nunca** grave um segredo literal no `.mcp.json`. Só OAuth (URL), `${VAR}` ou `{{resolve:...}}`.
- Prefira **OAuth**; só use token quando o servidor não oferecer OAuth.
- **Não** chame `get-secret-value`/`batch-get-secret-value` para "testar" — vaza a
  chave para o contexto. Valide por `/mcp`.
- Se não souber um valor per-projeto (`project_ref`, escopo), **pergunte** — não preencha lacuna.
