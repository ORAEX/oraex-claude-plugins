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

## Os três MCPs iniciais (mecanismo verificado)

| MCP | Transporte | Auth | Per-projeto |
|---|---|---|---|
| **Supabase** | HTTP **local** (`localhost:54321/mcp`) **ou** remoto (`mcp.supabase.com/mcp`) | **local: nenhuma** · remoto: **OAuth** no navegador | local: o próprio stack · remoto: `?project_ref=<ref>` |
| **GitHub** | HTTP remoto (`api.githubcopilot.com/mcp/`) | **PAT** em `Authorization: Bearer ${GITHUB_PAT}` | escopo do próprio PAT |
| **AWS** | via plugin `aws-core` | sessão **SSO** (sem segredo) | perfil SSO do ambiente |

- **Supabase:** três cenários, escolhidos **por projeto** — ver a seção abaixo.
  O local é de primeira classe, não exceção.
- **GitHub:** `${GITHUB_PAT}` é expandido **no launch** a partir do ambiente. O
  PAT vem do `.env.local`/`.envrc` — de preferência puxado do Secrets Manager
  (`oraex/dev/<id>/mcp/github`) pela skill [[env-conventions]], não de arquivo estático.
- **AWS:** não duplique — **ligue o `aws-core`**, que já fornece o MCP de AWS
  usando a sessão SSO. Um MCP de AWS próprio no `.mcp.json` só se o projeto exigir.

## Supabase: escolha o cenário por projeto

O Supabase tem **três** configurações válidas. Descubra qual o projeto usa antes
de gravar — muitos projetos da ORAEX rodam **local** via CLI, e esse é o caminho
padrão para eles, sem credencial nenhuma.

**1. Local (stack da Supabase CLI)** — o mais comum no dev. Sem segredo, sem
OAuth; depende de `supabase start` estar de pé.

```json
"supabase": { "type": "http", "url": "http://localhost:54321/mcp" }
```

**2. Remoto hospedado** — projeto na nuvem. OAuth no navegador na primeira vez
(PAT não é mais necessário). `project_ref` escopa ao projeto; `read_only=true`
salvo pedido explícito de escrita.

```json
"supabase": { "type": "http", "url": "https://mcp.supabase.com/mcp?project_ref=<SUPABASE_PROJECT_REF>&read_only=true" }
```

**3. Token estático** (self-hosted, ou cliente sem suporte a OAuth) — só quando
1 e 2 não servem. Aí vale o padrão `asm-exec` + Secrets Manager per-dev
(`reference/aws-setup.md`), nunca token literal no arquivo.

Regra prática: **local → cenário 1; nuvem com OAuth → cenário 2; nuvem sem OAuth
→ cenário 3.** Na dúvida entre local e nuvem, **pergunte** — não presuma.

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
2. **Escolha o cenário de Supabase** (local / remoto / token — ver seção acima).
   Se local, a URL é `http://localhost:54321/mcp` e não há mais nada a coletar.
   Se remoto, descubra o `project_ref` deste projeto (peça ou leia de config).
3. Copie `templates/mcp.json`, troque o placeholder `<SUPABASE_MCP_URL...>` pela
   URL do cenário escolhido, preencha os demais literais e escreva em `.mcp.json`
   na raiz do projeto. **Não** invente `project_ref` nem o cenário: se não souber
   se é local ou nuvem, pergunte.
4. Lembre o usuário: `aws sso login`; para GitHub, ter `GITHUB_PAT` no ambiente
   (idealmente via Secrets Manager — ver [[env-conventions]] e `reference/aws-setup.md`).
5. Valide: `/mcp` na sessão (ou `claude mcp list`). Supabase **local** conecta
   direto se o stack estiver de pé (`supabase start`); **remoto** pede login
   OAuth no navegador na primeira vez. `! Needs authentication` costuma ser esse
   OAuth pendente ou sessão SSO expirada.

> **Pacotes/endpoints de MCP mudam.** Antes de gravar, confirme o transporte e a
> URL atuais de cada servidor — este arquivo reflete o estado verificado na data
> da última edição, não uma verdade permanente.

## Regras

- **Nunca** grave um segredo literal no `.mcp.json`. Só OAuth (URL), `${VAR}` ou `{{resolve:...}}`.
- Prefira **OAuth**; só use token quando o servidor não oferecer OAuth.
- **Não** chame `get-secret-value`/`batch-get-secret-value` para "testar" — vaza a
  chave para o contexto. Valide por `/mcp`.
- Se não souber um valor per-projeto (`project_ref`, escopo), **pergunte** — não preencha lacuna.
