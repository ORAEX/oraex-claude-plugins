# Publicar o quadro (e não perder a atualização de ninguém)

## Por que a página é estática

A página é HTML estático gerado do plano versionado, republicado no mesmo URL. Não usa a
capacidade `db` do Artifact: com estado na página haveria duas fontes da verdade
(página e repo) e alguém teria de reconciliá-las. O histórico já mora no git. Se um dia
for preciso marcar status pela página, a skill teria de ler o `db` e propor um commit no
plano. Isso não existe hoje, de propósito.

## O carimbo

`render` grava no topo da página:

```html
<script type="application/json" id="plan-source">
{"plan_id": "...", "plan_file": "docs/X.plan.json", "commit": "<sha do HEAD>",
 "plan_hash": "<hash do conteúdo, sem artifact.url>", "dirty": false, "rendered_at": "..."}
</script>
```

`render` recusa plano com mudança fora do commit (`--allow-dirty` só para pré-visualizar,
e a página mostra um aviso). Gravar só a `artifact.url` não conta como mudança.

## Passo a passo

1. **Atualize o checkout.** `git pull --ff-only` antes de editar o plano.
2. **Edite, valide e faça commit** do plano (e do doc, se escreveu Registro).
3. **Renderize** para o scratchpad da sessão:
   `python3 <skill>/scripts/plan.py render docs/X.plan.json -o <scratchpad>/<id>.html`
4. **Primeira publicação** (`artifact.url` é `null`):
   - Artifact `publish` com `file_path` = o HTML, `icon: "timeline"` e uma `description`
     de uma frase ("Quadro de fases do plano X, gerado de docs/X.plan.json").
   - Grave a URL devolvida em `artifact.url` e faça commit ("chore(plano): URL do quadro").
5. **Republicação** (há `artifact.url`):
   - Baixe a página publicada: Artifact `action: "read"` com `url` e `path: "index.html"`.
     A leitura salva o arquivo e diz onde (é ele que vai para o `compare`).
   - Se esta sessão ainda não leu nem publicou esse URL, faça também um `read` só com `url`
     (sem `path`). A cópia por `path` não conta como "ter visto" a versão, e sem essa
     leitura o publish é recusado.
   - `python3 <skill>/scripts/plan.py compare docs/X.plan.json <arquivo salvo pela leitura>`
   - Siga o resultado:

| Resultado | Saída | O que fazer |
|---|---|---|
| `igual` | 0 | A página já mostra este conteúdo. Republicar é opcional |
| `à frente` | 0 | O local contém o commit publicado. Publique com `url` + `file_path` |
| `novo` | 0 | Página sem carimbo (nunca foi deste script). Publique |
| `atrás` | 2 | A página veio de um commit mais novo. `git pull`, renderize, compare de novo |
| `divergente` | 2 | Cada lado tem commit que o outro não tem. `git pull` (resolva conflito no plano, se houver), commit, renderize, compare |
| `desconhecido` | 3 | O commit publicado não existe aqui. `git fetch` e compare. Se continuar, quem publicou não deu push: avise e não publique por cima |
| `erro` | 1 | Plano com mudança sem commit, ou página de outro plano. Corrija e repita |

6. **Recusa do Artifact.** Se o publish for recusado porque existe versão mais nova, a
   recusa entrega a versão publicada. Salve-a, rode `compare` e siga a tabela. Depois de
   um `git pull`, a nova renderização já contém a mudança do outro dev, e é isso que
   significa "fazer o merge" aqui: a página é derivada do repo, não se edita o HTML.
   **Nunca use `force`.** Ele descarta a versão do outro dev, e se o commit dele não
   estiver no seu checkout a mudança some da página.

## Por que isso não perde atualização

- A página só sai de commit, e o `compare` só deixa publicar quando o commit local
  **contém** o commit publicado. Logo, toda publicação nova inclui tudo que a anterior
  mostrava.
- Duas edições concorrentes no plano viram um merge do git. Fases diferentes não
  conflitam (um campo por linha). Mesma fase vira conflito explícito, resolvido por gente.
- Se um dev publica sem dar push, o outro recebe `desconhecido` e espera, em vez de
  sobrescrever.

## Quem pode publicar

O artifact nasce privado e pertence a quem publicou primeiro. Para o time republicar no
mesmo URL, o dono compartilha a página no claude.ai com **acesso de edição** para cada
dev. Quem só tem leitura recebe recusa ao publicar. Nesse caso, avise o usuário e não
crie outro artifact, senão o plano passa a ter duas URLs.

## Mostrar o plano

"mostra o plano" é leitura. Rode `summary` e responda com ele mais o link. Republicar
só se o plano mudou desde a última publicação, ou se o usuário pedir.
