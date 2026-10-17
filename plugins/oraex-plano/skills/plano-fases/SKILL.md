---
name: plano-fases
description: Plano em fases/fatias (F1, F2a, F2b…) e o quadro dele. Use sempre que a conversa tocar um plano em fatias: criar o plano ou quebrar um design-doc em fatias com critério de aceite; começar ou fechar uma fatia ("fechei a F2b", "bora começar a F3a", "escrevi o Registro — F2b"); registrar decisão ou bloqueio de uma fatia ("decidimos a D2", "surgiu um bloqueio na F2c"); ou perguntar o andamento ("mostra o plano", "qual o status do plano", "em que fatia estamos"). Mantém o plano versionado em docs/<PLANO>.plan.json e republica o quadro (Artifact) no mesmo URL, por isso use mesmo quando a mudança parecer só uma linha no doc: sem a skill o plano e o quadro ficam desatualizados. Não use para to-do do dia, checklist avulso, debug de uma fatia, roadmap ou deck de cronograma.
---

# Plano em fases com quadro no Artifact

O **arquivo versionado é a fonte da verdade**: `docs/<PLANO>.plan.json`, ao lado do
design-doc `docs/<PLANO>.md`. O doc guarda o desenho e as seções "Registro — Fx"; o
plano guarda fases, status, critérios de aceite, decisões, bloqueios e a URL do quadro.
O quadro (Artifact) só **mostra** o plano, carimbado com o commit de onde veio. Nunca
mude status pela página nem guarde estado nela.

O script `scripts/plan.py` (Python 3, sem dependências) fica no diretório base desta
skill. Ele valida, resume, renderiza e compara. Rode-o pelo caminho absoluto.

| Comando | Para quê |
|---|---|
| `plan.py validate PLAN` | Schema. Erro aponta o campo (`phases[3] (F2c): ...`) |
| `plan.py summary PLAN` | Resumo curto para o terminal, com o link do quadro |
| `plan.py phase PLAN F2b --status done` | Muda o status e preenche as datas |
| `plan.py render PLAN -o OUT.html` | Gera a página. Recusa plano com mudança sem commit |
| `plan.py compare PLAN LIVE.html` | Local × publicado: `igual`/`à frente` (0), `atrás`/`divergente` (2), `desconhecido` (3) |

Schema completo e exemplos de cada campo: `references/schema.md`. Plano de exemplo:
`examples/PORTAL_CLIENTE.plan.json`.

## Achar o plano

Procure `docs/*.plan.json` no repo. Com mais de um, use o que o usuário citou ou
pergunte. Antes de editar, `git pull --ff-only`: quem tem o pull mais recente vence, e
editar em cima de um plano velho cria conflito à toa.

## Quando agir

**Criar o plano** ("vamos planejar em fases X"). Escreva o design-doc e o plano
partindo de `assets/plan.template.json`: 1 fase por fatia, cada uma com o que entrega e
um critério de aceite **verificável**. A primeira fatia fica `next` (ou `in_progress`).
No doc, troque a tabela de fatias por um ponteiro para o plano, para não duplicar
status. Valide, faça commit e publique o quadro pela primeira vez.

**Começar uma fatia.** `phase PLAN Fx --status in_progress`, atualize `next_action`,
commit, publique.

**Fechar uma fatia** ("fechei a F2b"). Primeiro o doc: escreva a seção
`## Registro — F2b (AAAA-MM-DD)`. O quadro a encontra pelo cabeçalho e mostra o texto.
Depois o plano: `phase PLAN F2b --status done`, marque a próxima como `next` ou
`in_progress`, adicione os links da fatia (commits, PR), atualize `next_action` e
resolva bloqueios/itens que ela fechou. Commit e publique.

**Mudar decisão ou bloqueio.** Edite `decisions`/`blockers`/`open_items` (decidida
precisa do texto em `decision`; resolvido ganha `resolved_on`). Valide, commit, publique.

**Consultar** ("mostra o plano", "qual o status"). Rode `summary` e responda no terminal
com o resumo em poucas linhas mais o link do quadro. Não republique só porque
perguntaram. Republique se o plano mudou desde a última publicação ou se a página está
atrás do repo.

Em todos os casos de escrita, o commit vem antes da publicação, porque a página carimba
o commit e o `compare` depende dele. Se o projeto não autorizou commits sem perguntar,
peça o OK numa linha ("commito o plano e republico o quadro?"). O push segue o fluxo
normal do projeto; lembre que outro dev só enxerga a mudança depois dele.

## Publicar

Siga `references/publicacao.md`. Em resumo:

1. `render PLAN -o <scratchpad>/<id-do-plano>.html` (o seu diretório de scratchpad).
2. Sem `artifact.url` no plano: publique o arquivo como Artifact novo (`icon: "timeline"`,
   `description` de uma frase), grave a URL em `artifact.url` e faça commit.
3. Com URL: baixe a página publicada (Artifact `action: "read"`, `url` + `path: "index.html"`)
   e rode `compare` contra o arquivo salvo. Se esta sessão ainda não leu nem publicou esse
   artifact, faça também um `read` só com `url`, senão o publish é recusado. Só publique (com `url`) quando der
   `igual` ou `à frente`. `atrás`/`divergente`: `git pull`, renderize de novo, compare de novo.
   `desconhecido`: `git fetch`. Se continuar, quem publicou não deu push; avise e espere.
4. Se o Artifact recusar por haver versão mais nova, trate como o passo 3 com a versão que
   a recusa entrega. **Nunca use `force`**: ele apagaria a publicação de outro dev.

Na primeira publicação, quem cria o artifact é o dono dele. Para outro dev republicar no
mesmo URL, o dono compartilha a página com acesso de edição no claude.ai.
