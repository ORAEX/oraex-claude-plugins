---
name: revisao-ui
description: Revisa uma tela, componente ou fatia de UI de um produto ORAEX contra a baseline de identidade visual — token semântico em vez de cor crua (o que torna o produto tematizável e a marca trocável), par tipográfico Archivo/IBM Plex, logo por slot, padrões de composição (eyebrow, stat card, step badge), código-EN/UI-PT-BR, acessibilidade AA em light/dark/tema-cliente, e os quatro estados de tela. Use quando o usuário pedir revisão de UI/visual/front, revisar um componente ou tela nova, checar se algo respeita a identidade ORAEX, ou antes de fechar uma fatia que mexe em interface.
disallowed-tools: Edit, Write, NotebookEdit
---

# Revisão: a UI respeita a identidade visual ORAEX?

Revise **uma tela, componente ou fatia de UI** contra a baseline de identidade
da ORAEX. Não é revisão de arquitetura (para isso, `revisao-design`), nem de
bug/lógica (`code-review`), nem de isolamento de tenant (`revisao-seguranca`).
O alvo é a **camada visual**: JSX/TSX, CSS/Tailwind, tokens, composição.

Antes de revisar, **leia a baseline**:
`${CLAUDE_PLUGIN_ROOT}/references/identidade-visual.md`. Ela é a fonte de
verdade; este arquivo é o procedimento. Funciona em qualquer projeto ORAEX
(finx/crmx/itsmx compartilham a identidade).

## O que estou protegendo

A identidade existe para os produtos ORAEX parecerem **um sistema** — sóbrio,
institucional, "consultoria global" — e para nascerem **multi-tenant**, prontos
a receber a marca de um cliente sem reescrita. Uma tela que fere isso cobra
retrabalho (retematização impossível, inconsistência entre módulos, a11y
quebrada). Revise por evidência: cite `arquivo:linha` e diga se **cumpre**,
**fere** ou **é omisso**. Não invente elogio nem problema.

## Verifique um a um

### 1. Token semântico, nunca cor crua  ⟵ o mais importante

- Há `#hex`, `rgb(...)`, `oklch(...)` ou `bg-[#...]`/`text-[...]` **cravado num
  componente**, fora do `globals.css`/da baseline? Cada ocorrência é um furo: é
  o que impede tematizar e trocar a marca por cliente.
- O componente usa o token **certo pelo papel** (`bg-primary`, `text-muted-
  foreground`, `border-border`), não um vizinho parecido "que dá no mesmo"?
- Cor de **status** foi usada como decoração, ou reservada a significado
  (`destructive` só para destrutivo/erro)?

### 2. Tipografia

- Título em **Archivo**, corpo em **IBM Plex Sans**? **Michroma** aparece **só**
  no wordmark, nunca em corpo/título?
- Valor monetário / coluna numérica usa **tabular-nums**?
- Ênfase inline é peso em navy (`foreground`), não cor de marca espalhada?

### 3. Logotipo

- O logo é referenciado por **slot/componente** (`<Logo …/>`), não por caminho
  de arquivo hardcoded?
- A **variante** casa com a superfície (azul em fundo claro, branco em navy) e
  com o espaço (mark vs mark+tagline)?

### 4. Padrões de composição

- Seções usam o **eyebrow label** (maiúscula, tracking, primary) quando cabe?
- Cards, stat cards, step badges e tabelas seguem o padrão da baseline (borda
  fina, acento em vez de preenchimento chapado, header navy em tabela)?
- A tela respeita o registro **light-first, arejado** — ou está apinhada / com
  cor de marca chapando áreas grandes?

### 5. Idioma — código EN, UI PT-BR

- Nome de componente/prop/token em **inglês**?
- Todo texto lido pelo usuário em **PT-BR** (label, placeholder, empty, erro,
  tooltip)? Sobrou string em inglês na UI?
- Moeda/data/número via `Intl`/`pt-BR`, não formatação manual?

### 6. Acessibilidade

- Contraste **AA** de pé em **light e dark** (e, se houver, num tema-cliente de
  amostra)? Combinação texto/fundo suspeita citada com o par de tokens.
- **Foco visível** (sem `outline:none` órfão)? Alvo de toque adequado?
- Cor **não** é o único portador de significado (status leva ícone/texto)?
- Controles com `aria`/label?

### 7. Os quatro estados

- Tela que carrega dado tem **loading (skeleton)**, **vazio**, **erro (com
  retry)** e **conteúdo**? Qual falta? Ausência é achado.

### 8. Pronto-para-tematizar (a costura, não o motor)

- A tela está **theming-ready** (100% token-only, a11y robusta), de modo que
  trocar o seed do tenant não a quebre?
- **Não** cobre aqui o *mecanismo* de tema por tenant — isso é `revisao-design`.
  Se a tela **assume** um mecanismo de tema, aponte para lá; não avalie a
  arquitetura você mesmo.

## Formato da resposta

Abra com um veredito de uma linha: **esta UI está pronta para fechar a fatia, ou
tem furo de identidade/a11y que precisa fechar antes?**

Depois, para cada ponto tocado:

- **Ponto:** qual dos 8
- **Situação:** `CUMPRE` · `FERE` · `OMISSO`
- **Evidência:** `arquivo:linha`
- **Consequência:** o retrabalho concreto (não tematizável, inconsistência, a11y
  reprovada…)
- **Ajuste mínimo:** a menor mudança que fecha (aponte o ponto, não reescreva a
  tela)

Feche com o que falta ao dono decidir (ex.: uma matiz de status, um padrão novo
que a baseline ainda não cobre).

## Regras

- **Não altere nenhum arquivo.** É revisão; a mudança é do dono.
- Ponto cumprido **conta** — diga que cumpre, não force achado.
- Não confunda preferência de estilo com furo de baseline. Só levante o que
  cobra retrabalho ou fere uma invariante da identidade.
- Separe o que a tela **faz** do que **omite** — omissão é achado, não suposição.
- Cor crua fora da baseline é **sempre** achado, por menor que pareça.
