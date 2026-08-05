---
name: env-conventions
description: Normatiza os arquivos de ambiente de um projeto no padrão ORAEX — .env (defaults não-secretos, versionado), .env.local (segredos, gitignored), .env.example (contrato do que existe) e .envrc (direnv, exporta ORAEX_DEV_ID/AWS_PROFILE/AWS_REGION). Use quando o usuário pedir para padronizar variáveis de ambiente, criar/organizar .env/.env.local/.envrc/direnv, definir o ORAEX_DEV_ID, ou preparar o ambiente de um projeto novo.
---

# Convenções de ambiente (padrão ORAEX)

Padroniza como cada projeto lida com variáveis de ambiente e identidade do dev.
É a base do baseline de MCP ([[mcp-baseline]]): o `ORAEX_DEV_ID` definido aqui é
o mesmo que nomeia o segredo no Secrets Manager e escopa o IAM por dev.

## Os quatro arquivos e seus papéis

| Arquivo | Contém | Git |
|---|---|---|
| `.env` | defaults **não-secretos** compartilhados (feature flags, URLs públicas) | **versionado** |
| `.env.local` | **segredos** e overrides da máquina | **gitignored** |
| `.env.example` | o **contrato**: toda chave que existe, com valor vazio/fake | **versionado** |
| `.envrc` | direnv: identidade e sessão (`ORAEX_DEV_ID`, `AWS_PROFILE`, `AWS_REGION`) | **versionado** |

Regra de ouro: **segredo nunca em arquivo versionado.** `.env` e `.env.example`
entram no git; `.env.local` nunca. Todo segredo real da ORAEX deve migrar para o
AWS Secrets Manager e ser consumido via `asm-exec` (ver [[mcp-baseline]]) — o
`.env.local` fica para o mínimo que não dá para resolver assim.

## `.envrc` (direnv)

O `.envrc` é o que faz o `${ORAEX_DEV_ID}` existir no ambiente quando você abre
o Claude Code no projeto. Requer `direnv` instalado e `direnv allow` no repo.

```bash
# .envrc — versionado (não tem segredo)
export ORAEX_DEV_ID="athos"          # estável por dev; nomeia o segredo e a DevId do IAM
export AWS_PROFILE="oraex-sso"        # perfil SSO
export AWS_REGION="us-east-1"

# PAT do GitHub para o MCP remoto: puxado do Secrets Manager (não fica em arquivo).
# Requer sessão SSO ativa (aws sso login) e o asm-exec do plugin aws-core.
export GITHUB_PAT="$(asm-exec -- printf %s \
  '{{resolve:secretsmanager:oraex/dev/'"$ORAEX_DEV_ID"'/mcp/github:SecretString:token}}')"

# demais segredos que ainda não estão no Secrets Manager: mantenha em .env.local
dotenv_if_exists .env.local
```

> `ORAEX_DEV_ID` é o eixo do baseline: mesmo valor em `.envrc` → nome do segredo
> (`oraex/dev/<id>/mcp/*`) → tag `DevId` no IAM. Escolha um id curto e estável
> por pessoa; não use o usuário do SO (varia entre máquinas).

> **Trade-off aceito:** o MCP remoto do GitHub exige o PAT como header, então ele
> vive no ambiente do processo (é a escolha "remoto HTTP"). Puxá-lo do Secrets
> Manager no `.envrc` evita o PAT num arquivo estático e centraliza a rotação,
> mas ele ainda fica em memória do shell. Quem quiser o PAT fora do ambiente deve
> usar o GitHub via Docker local + `asm-exec` (resolve em runtime).

## Procedimento

1. Garanta o `.gitignore`: `.env.local` (e variantes `*.local`) ignorados; `.env`
   e `.env.example` **não**.
2. Crie/atualize `.env.example` listando toda variável usada no projeto, com
   valores vazios ou claramente falsos. É o contrato de onboarding.
3. Crie o `.envrc` com `ORAEX_DEV_ID`, `AWS_PROFILE`, `AWS_REGION`. Peça ao
   usuário o `ORAEX_DEV_ID` dele se não houver um definido.
4. Se algum segredo estiver hoje versionado num `.env`, sinalize como incidente:
   mover para `.env.local` (ou Secrets Manager) e **rotacionar** a chave exposta.

## Regras

- Nunca escreva um segredo em arquivo que vá para o git.
- Não invente valores em `.env.example` que pareçam reais — vazio ou `changeme`.
- Se achar segredo commitado, **pare e avise**: mover não basta, tem de rotacionar.
