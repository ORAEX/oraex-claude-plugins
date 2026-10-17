# plano-fases

Acompanha um plano em fases (fatias F1, F2a, F2b…) e mantém um quadro das fases num
Artifact do claude.ai, sempre no mesmo URL. O quadro fica aberto ao lado do terminal e
mostra a fase atual, o critério de aceite de cada fase, bloqueios, decisões em aberto,
pendências e os registros de fechamento.

O plano mora no repo (`docs/<PLANO>.plan.json`, ao lado do design-doc). O quadro só
mostra o que está commitado.

## Onde está instalada

Plugin `oraex-plano`, skill `plano-fases`, no marketplace `oraex`
(`oraex-claude-plugins/plugins/oraex-plano/skills/plano-fases`).

```bash
claude plugin marketplace add ~/projects/oraex-claude-plugins   # uma vez por máquina
claude plugin install oraex-plano@oraex
```

Para o time, habilite em `.claude/settings.json` do projeto
(`"enabledPlugins": { "oraex-plano@oraex": true }`). Ver o README do marketplace.

## Como usar

| Você diz | O que acontece |
|---|---|
| "vamos planejar em fases o portal do cliente" | Cria `docs/PORTAL_CLIENTE.md` e `docs/PORTAL_CLIENTE.plan.json`, faz commit e publica o quadro. A URL fica gravada no plano |
| "bora começar a F2a" | Marca a fase como em andamento, commit, republica |
| "fechei a F2b" | Escreve o `## Registro — F2b` no doc, fecha a fase, marca a próxima, anexa commits/PR, commit, republica |
| "decidimos a D2: …" / "surgiu um bloqueio na F2c" | Atualiza decisões/bloqueios, commit, republica |
| "mostra o plano" | Resumo curto no terminal + link do quadro |

O script também roda sozinho:

```bash
S=~/.claude/plugins/cache/oraex/oraex-plano/<versão>/skills/plano-fases/scripts
python3 $S/plan.py validate docs/PORTAL_CLIENTE.plan.json
python3 $S/plan.py summary  docs/PORTAL_CLIENTE.plan.json
python3 $S/plan.py phase    docs/PORTAL_CLIENTE.plan.json F2b --status done
python3 $S/plan.py render   docs/PORTAL_CLIENTE.plan.json -o /tmp/quadro.html
python3 $S/test_plan.py     # testes (stdlib)
```

## Mais de um dev

- Qualquer dev republica no mesmo URL. Antes, a skill compara o commit carimbado na
  página com o checkout local e só publica se o local **contém** o que está publicado.
  Se não contém, ela pede `git pull`. Detalhes em `references/publicacao.md`.
- O artifact pertence a quem publicou primeiro. Ele precisa compartilhar a página com
  **acesso de edição** com o time (menu Share no claude.ai), senão os outros não
  conseguem republicar.
- Nunca se usa `force` no publish.

## Arquivos

```
SKILL.md                    gatilho + fluxo (o que o Claude lê)
scripts/plan.py             validate · summary · phase · render · compare (stdlib)
scripts/test_plan.py        testes, incluindo dois devs publicando de checkouts diferentes
references/schema.md        schema do plano e por que JSON num arquivo separado
references/publicacao.md    publicação, carimbo de origem e conflito entre devs
assets/plan.template.json   esqueleto de plano novo
assets/page.html            template da página (tokens da identidade ORAEX, claro/escuro)
examples/                   plano de exemplo (fictício) com design-doc e registros
```
