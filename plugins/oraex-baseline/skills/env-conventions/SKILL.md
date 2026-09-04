---
name: env-conventions
description: Normatiza os arquivos de ambiente de um projeto no padrão ORAEX — .env (defaults não-secretos, versionado), .env.local (segredos, gitignored), .env.example (contrato do que existe) e .envrc (direnv, exporta ORAEX_DEV_ID/AWS_PROFILE/AWS_REGION). Use quando o usuário pedir para padronizar variáveis de ambiente, criar/organizar .env/.env.local/.envrc/direnv, definir o ORAEX_DEV_ID, ou preparar o ambiente de um projeto novo.
---

# Convenções de ambiente (padrão ORAEX)

Padroniza como cada projeto lida com variáveis de ambiente e identidade do dev.
É a base do baseline de MCP ([[mcp-baseline]]): o `ORAEX_DEV_ID` definido aqui é
o handle (sem `@`) que **nomeia o parâmetro no SSM Parameter Store**; a
autorização per-dev é por **tag** `DevId` (o `userName`/e-mail do Identity
Center). Ver [[mcp-baseline]] e `reference/aws-setup.md`.

## Os quatro arquivos e seus papéis

| Arquivo | Contém | Git |
|---|---|---|
| `.env` | defaults **não-secretos** compartilhados (feature flags, URLs públicas) | **versionado** |
| `.env.local` | **segredos** e overrides da máquina | **gitignored** |
| `.env.example` | o **contrato**: toda chave que existe, com valor vazio/fake | **versionado** |
| `.envrc` | direnv: sessão compartilhada (`AWS_PROFILE`, `AWS_REGION`) e sourcing do `.envrc.local` | **versionado** |
| `.envrc.local` | identidade **POR-DEV** (`ORAEX_DEV_ID`, o handle sem `@`) | **gitignored** |
| `.envrc.local.example` | o **contrato** do handle per-dev (copie para `.envrc.local`) | **versionado** |

Regra de ouro: **segredo nunca em arquivo versionado.** `.env` e `.env.example`
entram no git; `.env.local` nunca. Segredos reais da ORAEX moram no **AWS SSM
Parameter Store** (`SecureString`), puxados para o env no `.envrc` (ver
[[mcp-baseline]] e `reference/aws-setup.md`). O `.env.local` fica para o mínimo
que não dá para resolver assim. (Secrets Manager + `asm-exec` seguem para o caso
de resolução em runtime, com o segredo nunca no env.)

## `.envrc` (direnv)

O `.envrc` é o que faz o `${ORAEX_DEV_ID}` existir no ambiente quando você abre
o Claude Code no projeto. Requer `direnv` instalado e `direnv allow` no repo.

O `.envrc` é **versionado e igual para toda a ORAEX** — por isso NÃO carrega o
handle: `ORAEX_DEV_ID` é per-dev e vive no `.envrc.local` (gitignored), sourciado
no topo do `.envrc`. Se o handle fosse hardcoded no arquivo versionado, todo dev
novo herdaria o mesmo handle (lendo o SSM de outra pessoa, sem acesso) e qualquer
correção viraria conflito de merge recorrente.

Esta skill **gera** o `.envrc` a partir de `templates/envrc` e o
`.envrc.local` a partir de `templates/envrc.local.example`, preenchendo os
valores (todos **não-secretos**) que coleta interativamente com você — não é para
editar à mão. Os blocos abaixo são o que ela produz:

```bash
# .envrc — versionado (não tem segredo, não tem handle)
source_env_if_exists .envrc.local     # traz o ORAEX_DEV_ID per-dev (gitignored)

export AWS_PROFILE="${AWS_PROFILE:-oraex-dev}"   # profile SSO do AWSDeveloperAccess (não-admin)
export AWS_REGION="${AWS_REGION:-sa-east-1}"

if [ -z "${ORAEX_DEV_ID:-}" ]; then
  echo "env-conventions: ORAEX_DEV_ID não definido — copie .envrc.local.example para .envrc.local." >&2
fi

# PAT do GitHub para o MCP remoto: puxado do SSM Parameter Store (não fica em arquivo).
# Só chama o SSM se houver handle. Requer sessão SSO ativa (aws sso login --profile oraex-dev).
if [ -n "${ORAEX_DEV_ID:-}" ]; then
  if GITHUB_PAT="$(aws ssm get-parameter --name "/oraex/dev/$ORAEX_DEV_ID/mcp/github" \
      --with-decryption --query 'Parameter.Value' --output text \
      --region "$AWS_REGION" --profile "$AWS_PROFILE" 2>/dev/null)"; then
    export GITHUB_PAT
  fi
fi

# demais segredos ainda fora do Parameter Store: mantenha em .env.local
dotenv_if_exists .env.local
```

```bash
# .envrc.local — POR-DEV, gitignored. Cada dev põe o SEU handle.
export ORAEX_DEV_ID="seu.handle"     # handle SEM @; compõe o NOME do parâmetro SSM
```

> `ORAEX_DEV_ID` é o **handle sem `@`** que compõe o nome do parâmetro
> (`/oraex/dev/<handle>/mcp/*`). A **autorização** é por tag `DevId` = seu
> `userName` do Identity Center (o e-mail), emitida como session tag pela ABAC —
> por isso o `@` do e-mail não atrapalha (tag aceita `@`; nome de parâmetro não).
> Escolha um handle curto e estável; não use o usuário do SO (varia entre máquinas).

> **Trade-off aceito:** o MCP remoto do GitHub exige o PAT como header, então ele
> vive no ambiente do processo (é a escolha "remoto HTTP"). Puxá-lo do Parameter
> Store no `.envrc` evita o PAT num arquivo estático e centraliza a rotação, mas
> ele fica em memória do shell. Quem quiser o PAT fora do ambiente usa o GitHub
> via Docker local + `asm-exec` (Secrets Manager, resolvido em runtime).

## Procedimento

1. Garanta o `.gitignore`: `.env.local` e `.envrc.local` (e variantes `*.local`)
   ignorados; `.env`, `.env.example` e `.envrc.local.example` **não**.
2. Crie/atualize `.env.example` listando toda variável usada no projeto, com
   valores vazios ou claramente falsos. É o contrato de onboarding.
3. **Gere o `.envrc` a partir de `templates/envrc`** (sem handle: ele apenas
   sourceia o `.envrc.local` e traz `AWS_PROFILE`/`AWS_REGION` com default
   overridável) e o **`.envrc.local.example` a partir de
   `templates/envrc.local.example`** (contrato versionado do handle). Colete
   interativamente os valores não-secretos: `AWS_PROFILE` (o profile SSO de dev,
   ex.: `oraex-dev`) e `AWS_REGION`, e o `ORAEX_DEV_ID` do dev (handle sem `@`).
   Pergunte cada um que não estiver definido — **não invente**. Escreva/atualize o
   **`.envrc.local` gitignored** com o handle coletado (para a máquina dele já
   funcionar) — o `.envrc` versionado **não** carrega handle. Adicione **uma linha
   de sourcing por MCP que use token** (o template já traz a do GitHub). `direnv
   allow` ao final.
4. Se algum segredo estiver hoje versionado num `.env`, sinalize como incidente:
   mover para `.env.local` (ou Parameter Store) e **rotacionar** a chave exposta.

## Regras

- Nunca escreva um segredo em arquivo que vá para o git.
- Não invente valores em `.env.example` que pareçam reais — vazio ou `changeme`.
- Se achar segredo commitado, **pare e avise**: mover não basta, tem de rotacionar.
