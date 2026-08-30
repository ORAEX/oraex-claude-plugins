---
name: revisao-design
description: Revisa uma decisão de arquitetura ou um design-doc contra os princípios de engenharia da ORAEX — multi-tenant desde o dia 1, fronteiras de módulo nítidas, código em inglês / UI em PT-BR, auditabilidade por padrão, integrações de terceiro isoladas em adapters, fonte de verdade única por entidade, e o processo "desenho gravado → validado → fatias com sanidade". Use quando o usuário pedir revisão de design/arquitetura, revisar um doc de fase antes de codar, avaliar se uma proposta respeita as fronteiras dos módulos, checar se um schema novo nasce multi-tenant, ou decidir se um design está pronto para virar fatias.
disallowed-tools: Edit, Write, NotebookEdit
---

# Revisão: o design respeita os princípios ORAEX?

Revise **uma decisão de arquitetura ou um design-doc** (não o código já escrito —
para bugs use `code-review`, para segurança de tenant use `revisao-seguranca`).
O alvo é o **desenho**: um doc em `docs/`, uma proposta na conversa, ou o
formato de um schema/módulo antes de virar migration.

Funciona em qualquer projeto ORAEX (crmx/finx/itsmx compartilham estes
princípios). As referências ao itsmx abaixo são exemplo, não pré-requisito.

## O que estou protegendo

Os princípios de arquitetura da ORAEX (CLAUDE.md §4) existem para o sistema
crescer sem virar bola de barro e para eventualmente virar produto multi-tenant.
Um design que os fere hoje cobra retrabalho caro depois. Revise contra cada um,
por evidência: cite `arquivo:linha` (ou o trecho da proposta) e diga se o design
**cumpre**, **fere** ou **é omisso**. Não invente elogio nem problema.

## Os princípios (verifique um a um)

### 1. Multi-tenant desde o dia 1

- Toda entidade central do design carrega `organization_id`? O isolamento é
  delegado ao **banco** (RLS), não a filtro de aplicação?
- Tabela nova sem tenant guard é um débito que nasce embutido — o design diz
  explicitamente que ela recebe os guards (RLS + auditoria)?
- Se o design introduz um caminho **sem sessão de usuário** (webhook, job,
  route handler), ele diz como o tenant é resolvido ali?

### 2. Fronteiras de módulo nítidas

- O design faz um módulo depender do **detalhe interno** de outro (tabela,
  função privada), em vez de uma fronteira pública? (RH/turnos, timesheet,
  contratos, tickets, integrações, financeiro são módulos separados.)
- Integração com sistema de terceiro está **isolada em adapter** (um módulo por
  sistema externo), de modo que a lógica de negócio nunca dependa do formato do
  parceiro? (CLAUDE.md §7.)
- Regra de negócio pura está separada de I/O (padrão `*-rules.ts` puro vs.
  domínio que abre transação)?

### 3. Código em inglês, UI em PT-BR

- Nomes de tabela/coluna/função/arquivo no design estão em **inglês**?
- Termo de domínio em português (CLT, PJ, apontamento, turno, conciliação)
  aparece só como **label de UI**, nunca como nome de campo no banco?

### 4. Auditabilidade por padrão

- Alterações em dado sensível (timesheet, apontamento, cadastro de colaborador,
  o que o design tocar) geram **registro de auditoria** (quem/quando/antes/depois)?
- A auditoria é automática (trigger), não dependente de a aplicação lembrar?

### 5. Fonte de verdade única por entidade

- O design **duplica** um dado que é dono de outro sistema/módulo? (Ex.: repetir
  valor comercial que é do financeiro, ou dado de cliente que é do CRM.) A
  fronteira de propriedade está explícita?
- Onde há master em transição (ex.: Cliente hoje no ITSM, alvo no CRM), o design
  deixa o gancho (`external_crm_id` nullable) sem se acoplar cedo demais?

### 6. Altitude e simplicidade

- O design **sobre-projeta** para um requisito que ainda não existe? (Tabela,
  camada ou abstração que só se paga num cenário futuro incerto.) Prefira a
  menor superfície que resolve o caso real de hoje, com a porta aberta para
  depois — não a porta já construída.
- Ou o oposto: corta um canto que **vai** cobrar retrabalho previsível (schema
  estreito que já se sabe que vai generalizar)? O CLAUDE.md tem precedente:
  `work_items` nasceu tipado de propósito.

### 7. Processo ORAEX de design

- Decisões marcadas como **[ASSUNÇÃO]** (definidas sem o dono confirmar) estão
  sinalizadas como tal, e não travestidas de fato fechado?
- O design está **gravado** (doc versionado em `docs/`), não só na conversa?
- Ele se decompõe em **fatias** com critério de pronto (a sanidade de sempre:
  `test` · `typecheck` · `biome` · `build` · `test:integration`) e migration
  incremental quando toca schema?
- As decisões downstream/adiadas estão **listadas** (não esquecidas)?

## Formato da resposta

Abra com um veredito de uma linha: **este design está pronto para virar fatias,
ou tem furo de princípio que precisa fechar antes?**

Depois, para cada princípio tocado:

- **Princípio:** qual dos 7
- **Situação:** `CUMPRE` · `FERE` · `OMISSO`
- **Evidência:** `arquivo:linha` ou o trecho da proposta
- **Consequência:** o retrabalho concreto que o furo cobra depois
- **Ajuste mínimo:** a menor mudança de desenho que fecha (não reescreva o
  design — aponte o ponto)

Feche com as **decisões que faltam ao dono tomar** antes de codar (as que são
genuinamente dele, não detalhe que o design pode assumir).

## Regras

- **Não altere nenhum arquivo.** Isto é revisão de desenho; a decisão é do dono.
- Princípio cumprido **conta** — diga que está cumprido, não force achado.
- Não confunda preferência de estilo com furo de princípio. Só levante o que
  cobra retrabalho ou fere uma invariante do CLAUDE.md.
- Separe o que o design **afirma** do que ele **omite** — omissão é achado, não
  suposição sua.
