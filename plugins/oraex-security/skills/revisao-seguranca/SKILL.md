---
name: revisao-seguranca
description: Revisa isolamento de tenant e auditabilidade num stack multi-tenant da ORAEX — se toda escrita passa pelo wrapper de tenant, se toda tabela com organization_id tem RLS + trilha de auditoria, se o service-role é contido, e se rotas sem sessão de usuário (route handlers, webhooks, jobs) resolvem tenant e aplicam guard. Use quando o usuário pedir revisão de segurança, auditar RLS/multi-tenant, revisar uma migration nova, checar vazamento entre tenants, revisar um endpoint/webhook, ou antes de fechar uma fatia que mexe em schema ou em escrita de dados.
disallowed-tools: Edit, Write, NotebookEdit
---

# Revisão: isolamento de tenant e auditabilidade

Revise o repositório atual procurando **quebras de isolamento entre tenants e
de trilha de auditoria** — e só isso. Não faça revisão geral de segurança
(injeção, XSS, dependências): escopo estreito é o que torna a revisão
confiável. Para bypass de MFA/segundo fator, use a skill `audit-mfa` — é outra
falha.

Funciona em qualquer stack multi-tenant da ORAEX. As pistas de Supabase/Postgres
+ Next abaixo são atalhos, não pré-requisito — o nome do wrapper e das funções
muda entre projetos (crmx/finx/itsmx), a **invariante** não.

## O princípio

Num sistema multi-tenant, o isolamento não pode morar na camada de aplicação
("o `WHERE organization_id = ?` que o dev lembrou de escrever"). Ele mora no
**banco**: RLS que o Postgres aplica sozinho, mesmo que a query esqueça o
filtro. A pergunta central de toda a revisão é:

> Se este código esquecer o filtro de tenant, o banco ainda barra? E se
> alguém escrever nesta tabela, fica registro de **quem** fez, **quando** e
> **o quê**?

Trabalhe por evidência: cite sempre `arquivo:linha` e **cole o trecho real**.
Se algo não existir, diga "não existe" — não presuma nem preencha lacunas.

## As invariantes (verifique uma a uma)

### 1. Toda query passa pelo wrapper de tenant

Encontre o wrapper de transação com escopo de tenant (no itsmx é `withTenant`,
que faz `SET LOCAL ROLE` + `set_config('app.current_org', …)` + `app.current_user`).

- Existe **uso de conexão crua ao banco fora do wrapper**? (grep pelo client
  direto — `dbDirect`, `db` cru, `pool.query`, `createClient(...service...)`.)
- Cada uso fora do wrapper é uma **exceção justificada e documentada**
  (ex.: resolver o tenant antes de ter contexto), ou é uma query de dados que
  deveria estar dentro? Liste **cada** ocorrência com `arquivo:linha`.
- O wrapper roda sob um **role sem privilégio** (`NOSUPERUSER`, `NOBYPASSRLS`)?
  Se o role da app puder furar RLS, todo o resto é decorativo.

### 2. Toda tabela com `organization_id` está guardada

Para **cada** tabela de domínio (que tem coluna `organization_id`), confirme as
três proteções — normalmente aplicadas por um helper na migration
(`apply_tenant_guards` ou equivalente):

- **RLS `ENABLE` + `FORCE`** com policy de isolamento
  (`USING (organization_id = current_org())`). `FORCE` importa: sem ele, o
  dono da tabela ignora a policy.
- **Trigger de auditoria** AFTER INSERT/UPDATE/DELETE gravando na trilha.
- **`updated_at`** mantido por trigger (se a coluna existir).

Prove com a migration. Uma tabela nova com `organization_id` **sem** a chamada
do helper é o achado mais comum e mais grave. Se o projeto tiver um teste de
rede que falha nesse caso (no itsmx, `tests/integration/tenant-guards.test.ts`),
confirme que ele cobre a tabela nova.

### 3. A trilha de auditoria é imutável e automática

- O `audit_log` (ou equivalente) é **append-only**? Existe policy que recusa
  UPDATE/DELETE nele?
- Ele é escrito **só por trigger**, nunca pela aplicação? Procure INSERT manual
  em `audit_log` no código de app — se existir, o ator pode ser forjado.
- O `actor_id` vem do **contexto de sessão do banco** (`app.current_user`), não
  de um parâmetro que o chamador escolhe?

### 4. Autorização e entitlement moram na app, não na RLS

A RLS faz **uma** coisa: isolar tenant. Ela **não** deve decidir papel
(owner/admin/member) nem módulo aceso.

- Procure policy de RLS que tente filtrar por papel ou por feature — é sinal de
  responsabilidade no lugar errado (frágil e difícil de auditar).
- A checagem de papel e de módulo (`requireModule`/`isModuleEnabled`,
  `canManage…`) acontece na server action / no route handler, **antes** da
  escrita? Falha fechada (nega por padrão)?

### 5. O service-role é contido e justificado

O client de service-role fura RLS por construção — é a maior superfície.

- Onde ele é instanciado? (`adminAuthClient`, `SERVICE_ROLE_KEY`.) Liste
  **todos** os usos com `arquivo:linha`.
- Cada uso é para uma operação que **só** o admin de Auth faz (convite,
  deletar fator, resolver e-mail) — ou ele está sendo usado para **ler/escrever
  dados de domínio**, furando o tenant? O segundo caso é achado grave.
- A chave de service-role nunca aparece em arquivo versionado (só em
  `.env.local`/cofre)? Confirme por grep no que está no git.

### 6. Rotas sem sessão de usuário resolvem tenant e aplicam guard

Route handlers, webhooks, cron/jobs e edge functions **não têm usuário logado**
— o padrão normal de resolver tenant (`getCurrentOrg` via `auth.getUser()`)
não vale ali. Para **cada** endpoint desse tipo:

- Como o **tenant** é resolvido? (segredo/id por conexão, token no path.) A
  resolução é confiável ou dá para um tenant forjar outro?
- Como a requisição é **autenticada**? (assinatura HMAC do corpo, token.) Um
  POST não assinado é recusado?
- A escrita ainda passa pelo **wrapper de tenant** com o `organization_id`
  resolvido (ator "sistema" quando não há usuário)? Ou ela escapa para o client
  cru e fura o isolamento?
- Há **idempotência** (dedup de evento) para reentrega não duplicar dado?

### 7. Segredos fora do versionado

- Grep por chaves/secrets em arquivos versionados (`.env`, `config.toml`,
  fixtures). O contrato ORAEX: `.env`/`.env.example` só carregam **defaults
  não-secretos**; segredo vive em `.env.local`/cofre, gitignored.

## Formato da resposta

Para cada achado:

- **Veredito:** `CONFIRMADO` (provei) · `PROVÁVEL` (só leitura) · `OK` (correto)
- **Invariante:** qual das 7 acima
- **Onde:** `arquivo:linha` + o trecho real
- **Cenário concreto:** quem escreve/lê o quê, e o que vaza ou fica sem trilha
- **Correção mínima:** o menor diff que fecha o buraco

Encerre com um veredito de uma linha: **o isolamento entre tenants deste
sistema é garantido pelo banco, ou depende de a aplicação lembrar do filtro?**

## Regras

- **Não altere nenhum arquivo.** Isto é revisão; a correção vem depois, em
  decisão separada.
- Não relate achado sem `arquivo:linha` e trecho.
- Invariante correta **conta como resultado** — diga que está correta, não
  invente achado para parecer produtivo.
- Distinga o que você **provou** (rodou query/teste) do que apenas **leu**.
