# Schema do plano (`schema_version: 1`)

Um arquivo JSON por plano, `docs/<PLANO>.plan.json`, ao lado do design-doc
`docs/<PLANO>.md`. `plan.py validate` aplica todas as regras abaixo e recusa campo
desconhecido (um `stauts` escrito errado vira erro, não um campo ignorado).

## Raiz

| Campo | Obrigatório | Tipo | Nota |
|---|---|---|---|
| `schema_version` | sim | `1` | |
| `id` | sim | texto | minúsculas, dígitos e hífen. Carimbado na página; o `compare` recusa página de outro plano |
| `title` | sim | texto | Nome do plano. Vira o `<title>` do quadro |
| `doc` | não | caminho | Design-doc, relativo ao arquivo do plano. É de onde saem os "Registro — Fx" |
| `repo.web_url` | não | URL | Base dos links (`https://github.com/org/repo`). Sem ele, o script deriva do `git remote origin` |
| `artifact.url` | não | URL ou `null` | URL do quadro (`https://claude.ai/artifact/...`). Gravada na primeira publicação |
| `next_action` | não | texto | A próxima coisa concreta a fazer. Aparece em destaque |
| `phases` | sim | lista | Pelo menos uma. A ordem da lista é a ordem da linha do tempo |
| `decisions` | não | lista | |
| `blockers` | não | lista | |
| `open_items` | não | lista | Pendências que não são bloqueio nem decisão |

## Fase

| Campo | Obrigatório | Nota |
|---|---|---|
| `id` | sim | `F1`, `F2a`… Único. É o que o cabeçalho "Registro — F2a" precisa citar |
| `title` | sim | |
| `delivers` | sim | O que a fatia entrega |
| `acceptance` | sim | Lista de critérios verificáveis (não vazia) |
| `status` | sim | `done` · `in_progress` · `next` · `pending` · `dropped` |
| `started` | se `in_progress` | `AAAA-MM-DD` |
| `finished` | se `done` | `AAAA-MM-DD`, não antes de `started`. Proibido em `next`/`pending` |
| `links` | não | `[{kind, ref, label?}]` |
| `notes` | não | Uma linha de contexto (ex.: "código pronto, falta staging") |

**Fase atual** (destacada no quadro): a primeira `in_progress`; sem nenhuma, a primeira
`next`; sem nenhuma, a primeira `pending`. Use `dropped` em vez de apagar uma fatia que
saiu do plano, para o histórico ficar visível.

### Links

| `kind` | `ref` | Vira |
|---|---|---|
| `commit` | SHA (7–40 hex) | `<web_url>/commit/<sha>` |
| `pr` | `#123` ou URL | `<web_url>/pull/123` |
| `doc` | caminho (relativo à pasta do doc, ou com `/` relativo à raiz), `#âncora` opcional | `<web_url>/blob/<commit>/<caminho>` |
| `url` | URL | ela mesma |

O link do **Registro** não precisa ser listado: o script encontra no `doc` o cabeçalho
`## Registro — <id> ...` (níveis 2 a 4, travessão, meia-risca ou hífen), linka a âncora
e mostra o texto da seção num bloco recolhível.

## Decisão

| Campo | Obrigatório | Nota |
|---|---|---|
| `id` | sim | `D1`… Único entre decisões e bloqueios |
| `question` | sim | |
| `status` | sim | `open` · `decided` |
| `decision` | se `decided` | O que foi decidido |
| `options` | não | Lista de textos (opções em consideração) |
| `decided_on` | não | `AAAA-MM-DD` |
| `phase` | não | id de uma fase existente |

## Bloqueio

| Campo | Obrigatório | Nota |
|---|---|---|
| `id` | sim | `B1`… |
| `description` | sim | |
| `status` | sim | `open` · `resolved` |
| `phase` | não | id de fase. Bloqueio aberto aparece no cartão e na linha do tempo da fase |
| `owner`, `since`, `resolved_on` | não | |

## Pendência (`open_items`)

`{ "text": "...", "status": "open" | "done", "phase"?: "F2c", "owner"?: "..." }`

## Texto

Campos de texto aceitam o markdown inline mínimo: `` `código` `` e `**negrito**`. O resto
sai como texto puro (HTML é escapado).

## Por que JSON num arquivo separado

Comparamos com um bloco estruturado dentro do design-doc. Ficou o arquivo separado:

- **Validação sem dependência.** JSON tem parser na biblioteca padrão do Python e do Node.
  YAML exigiria PyYAML ou um parser caseiro.
- **Merge limpo.** Indentado com um campo por linha, dois devs mexendo em fases
  diferentes não conflitam. Um bloco embutido mistura prosa e estrutura no mesmo diff.
- **Papéis separados.** O doc é prosa que só cresce (desenho e registros). O plano é o
  estado que muda. A duplicação que sobra é a tabela de fatias, e ela sai do doc, que
  passa a apontar para o plano.

O custo é editar JSON à mão. Na prática quem edita é o Claude, e `plan.py phase` cobre a
mudança mais comum. Se um dia o time quiser YAML, troque só a função `load` do script.
