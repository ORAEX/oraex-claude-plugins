# Identidade Visual ORAEX — baseline de produto

Fonte de verdade do **visual dos produtos ORAEX** (finx, crmx, itsmx…). Deriva do
reposicionamento de marca aprovado pelo comitê (2026) e da sua materialização em
produto (whitepaper "IA Corporativa"). As skills `revisao-ui` e o agente
`oraex-ui-review` revisam **contra este doc**.

Duas fronteiras a ter na cabeça o tempo todo:

- **Marca ≠ produto.** A marca (wordmark Michroma, tagline *Built to Decide.*,
  navy institucional, azul `#1E74C8`) é **decisão de comitê, imutável**. O
  produto **deriva** dela e adapta à densidade de um SaaS (light-first, leitura
  densa, números). Michroma é fonte de **wordmark**, nunca de corpo.
- **Tema de referência ≠ tema de cliente.** O tema ORAEX é o **default**. O
  sistema é multi-tenant (CLAUDE.md §1), então a arquitetura de token nasce
  pronta para um cliente sobrescrever a **marca** (seed) — sem que ninguém
  construa o motor de tema hoje. Ver "Contrato de tematização".

---

## 1. Cor — token em duas camadas

Regra-mãe, a que sustenta tudo: **componente consome token semântico, nunca
valor cru.** Nada de `#1E74C8`, `oklch(...)` ou `bg-[#...]` solto num componente.
É o que torna o produto tematizável e a marca trocável. A `revisao-ui` reprova
qualquer cor crua fora deste arquivo / do `globals.css`.

### Camada 1 — Seed (marca; um cliente pode sobrescrever)

| Token | Valor (light) | Papel |
|---|---|---|
| `--primary` | `oklch(0.554 0.152 252.4)` | Azul ORAEX `#1E74C8` |
| `--primary-foreground` | `oklch(1 0 0)` | Texto/ícone sobre primary |
| `--ring` | `oklch(0.554 0.152 252.4)` | Anel de foco = primary |
| `--radius` | `0.5rem` | Cantos (~8–10px do whitepaper) |

`--primary-foreground` é **derivado por contraste**, não fixado em branco: um
seed de cliente mais claro exige texto escuro. Ver "Contrato de tematização".

### Camada 2 — Semânticos (contrato fixo, derivado)

**Light (tema de referência):**

```css
--background:           oklch(1 0 0);
--foreground:           oklch(0.279 0.058 250.0);  /* #0F2A44 navy */
--card:                 oklch(1 0 0);
--card-foreground:      oklch(0.279 0.058 250.0);
--popover:              oklch(1 0 0);
--popover-foreground:   oklch(0.279 0.058 250.0);
--muted:                oklch(0.972 0.005 258.3);  /* #F4F6F9 */
--muted-foreground:     oklch(0.449 0.037 257.3);  /* #48566A slate */
--secondary:            oklch(0.958 0.015 251.2);  /* #EAF2FB */
--secondary-foreground: oklch(0.463 0.125 252.0);  /* #155A9C */
--accent:               oklch(0.921 0.028 248.1);  /* #D7E7F7 */
--accent-foreground:    oklch(0.279 0.058 250.0);
--border:               oklch(0.913 0.014 254.6);  /* #DCE3EC */
--input:                oklch(0.913 0.014 254.6);
```

**Status (fixo — não entra no seed; "semântico não vira marca"):**

```css
--destructive:            oklch(0.55 0.19 27);   /* ~#C5321C — AA em branco */
--destructive-foreground: oklch(1 0 0);
--success:                oklch(0.58 0.13 155);
--warning:                oklch(0.75 0.14 75);
```

**Dark (derivado):**

```css
.dark {
  --background:           oklch(0.190 0.028 250);
  --foreground:           oklch(0.970 0.010 250);
  --card:                 oklch(0.240 0.030 250);
  --card-foreground:      oklch(0.970 0.010 250);
  --popover:              oklch(0.240 0.030 250);
  --popover-foreground:   oklch(0.970 0.010 250);
  --muted:                oklch(0.280 0.030 250);
  --muted-foreground:     oklch(0.720 0.030 250);
  --primary:              oklch(0.620 0.150 252);
  --primary-foreground:   oklch(0.160 0.030 250);
  --secondary:            oklch(0.300 0.040 250);
  --secondary-foreground: oklch(0.900 0.030 250);
  --accent:               oklch(0.340 0.050 250);
  --accent-foreground:    oklch(0.970 0.010 250);
  --border:               oklch(1 0 0 / 12%);
  --input:                oklch(1 0 0 / 15%);
  --ring:                 oklch(0.620 0.150 252);
  --destructive:          oklch(0.70 0.17 25);
  --success:              oklch(0.70 0.13 155);
  --warning:              oklch(0.80 0.14 75);
}
```

Estes valores casam com o esquema shadcn/Tailwind v4 do finx (`app/globals.css`,
bloco `:root` / `.dark` + `@theme inline`). Trocar o tema cinza de fábrica por
estes é a primeira aplicação da baseline.

---

## 2. Tipografia

| Papel | Família | Uso |
|---|---|---|
| **Display / títulos** | **Archivo** (600–800) | H1–H3, números de destaque, stat cards |
| **Corpo / UI** | **IBM Plex Sans** (400–600) | Texto, labels, tabelas, formulários |
| **Wordmark** | **Michroma** | **Só** o logotipo ORAEX — nunca corpo |

- **Número tabular** (`font-variant-numeric: tabular-nums`) obrigatório em
  tabelas, valores monetários e qualquer coluna numérica — finx é financeiro,
  alinhamento de dígito importa.
- **Ênfase inline** em corpo = peso semibold na cor `--foreground` (navy), não
  cor de marca. Cor de marca em texto fica reservada a link e eyebrow.
- Escala sugerida (rem): 0.75 · 0.875 · 1 · 1.125 · 1.25 · 1.5 · 1.875 · 2.25.
  Leading apertado em título (~1.1), confortável em corpo (~1.5).

---

## 3. Logotipo nos sistemas

Logo **não é cor** — é **asset com variante escolhida por contexto**. Vive em
`assets/logo/` (SVG vetorizado: renderiza sem a fonte Michroma instalada).

- **Variante por superfície:** fundo claro → `oraex-logo-azul.svg`; fundo navy /
  sidebar escura → `oraex-logo-branco.svg`.
- **Lockup por espaço:** favicon / sidebar recolhida → só wordmark; login /
  splash → wordmark + tagline *Built to Decide.*
- **Nunca hardcode caminho** num componente de tela. Use um componente `<Logo
  surface="light|dark" lockup="mark|tagline" />` que resolve a variante — assim
  o logo é um **slot** único, e é onde o white-label troca a marca do cliente.
- Alvos: favicon, header da sidebar, tela de login, estado de loading, e-mail.

---

## 4. Padrões de composição (assinatura ORAEX)

O que faz uma tela "parecer ORAEX", extraído do whitepaper aprovado:

- **Eyebrow label** — rótulo em MAIÚSCULA, tracking largo, `--primary`, pequeno,
  acima do título de seção. É a marca registrada do layout.
- **Título Archivo navy** + **corpo IBM Plex slate** com ênfase inline navy.
- **Stat / hero card navy** — fundo `--foreground` (navy), número branco grande
  em Archivo, legenda azul-acinzentada, divisórias finas.
- **Cards com borda fina** (`--border`) + padding generoso; cor de marca como
  **acento** (borda, ícone, número), nunca preenchimento chapado.
- **Step badge** numerado (quadrado arredondado, `--primary`, número branco).
- **Tabela** com header navy, linhas claras, números tabulares.
- **Light-first, muito respiro**, régua fina azul separando blocos. Sóbrio,
  registro "consultoria global".

---

## 5. Idioma — código em inglês, UI em PT-BR

Mesma invariante da arquitetura (CLAUDE.md §3), aplicada à camada visual:

- Nome de componente/prop/token/arquivo em **inglês** (`InvoiceTable`,
  `--primary`, `emptyState`).
- Todo texto que o usuário lê em **PT-BR**: label, placeholder, empty state,
  mensagem de erro, tooltip, botão.
- Formatos **BR**: `Intl` com `pt-BR`, `R$`, data `dd/MM/yyyy`, número
  `1.234,56`. Nunca formatação manual de moeda/data.

---

## 6. Acessibilidade (não-negociável)

- **Contraste AA**: texto ≥ 4.5:1, UI/large ≥ 3:1 — e tem de valer em **light,
  dark e em qualquer seed de cliente** (não só no tema ORAEX).
- **Foco visível** sempre (`--ring`); nunca `outline:none` sem substituto.
- **Alvo mínimo** ~40px em toque.
- Cor **nunca** é o único portador de significado (status leva ícone/texto além
  da cor).
- `aria-*` e rótulo em todo controle; label associada a input.

---

## 7. Os quatro estados (toda tela de dado)

Tela que carrega dado precisa dos quatro — a ausência de um é achado da
`revisao-ui`:

1. **Loading** — skeleton (não spinner solto), preservando o layout.
2. **Vazio** — empty state com texto PT-BR e ação de saída.
3. **Erro** — mensagem clara + retry; nunca tela branca.
4. **Sucesso / conteúdo** — o estado normal.

---

## 8. Contrato de tematização (multi-tenant)

O produto nasce **tematizável**, mas **não se constrói o motor de tema hoje** —
só a costura (CLAUDE.md §6, altitude: *porta aberta, não porta construída*).

- **Seed sobrescrevível pelo cliente:** `--primary` (+ eventualmente um accent),
  `--radius`, e o **slot de logo**. Conjunto pequeno.
- **Fixo (não tematizável):** todos os semânticos de status
  (`--destructive/--success/--warning`) e a estrutura neutra. Cliente não pinta
  "excluir" de azul.
- **Derivação segura:** `--primary-foreground` sai por contraste sobre o seed
  (garante AA para qualquer marca), não fixo em branco.
- **Onde mora o mecanismo:** *como* o tema do tenant é guardado e injetado por
  request é **decisão de arquitetura** → design-doc revisado pela
  `revisao-design`, **não** pela `revisao-ui`. A `revisao-ui` só verifica se a
  **tela** está pronta: token-only, a11y de pé no tema ORAEX e num tema-cliente
  de amostra.

---

## Decisões downstream (listadas, não esquecidas)

- **[ADIADO]** Motor de resolução de tema por tenant (storage + injeção de CSS
  vars por request) — só quando houver cliente real pedindo white-label.
- **[ADIADO]** Sistema de ícones (o kit tem catálogo próprio; padronizar depois).
- **[ASSUNÇÃO]** Matizes de status (`success` verde, `warning` âmbar) definidas
  aqui, não pelo comitê de marca — revisáveis se surgir diretriz.
- **[ADIADO]** Dark mode como entrega formal — valores atuais são derivados,
  validados só em swatch.
