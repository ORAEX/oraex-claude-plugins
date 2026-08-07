# oraex-claude-plugins

Plugins da ORAEX para Claude Code. Este repositório é **duas coisas
ao mesmo tempo**:

- um **marketplace** (`.claude-plugin/marketplace.json` na raiz) — o catálogo;
- um ou mais **plugins** (`plugins/*/`) — o conteúdo instalável.

Essa é a razão de existir: escrever uma skill uma vez e instalá-la em
qualquer projeto por configuração, em vez de copiar arquivo entre repos.

## Plugins

| Plugin | Skills | Para quê |
|---|---|---|
| `oraex-security` | `audit-mfa` | Auditoria de MFA: verifica se o segundo fator é exigido pelo servidor ou apenas sugerido pela interface |
| `oraex-baseline` | `mcp-baseline`, `env-conventions` | Padroniza MCP por projeto (`.mcp.json` local com `asm-exec` + segredos per-dev no Secrets Manager, via SSO) e arquivos de ambiente (`.env`/`.env.local`/`.envrc`) |

## Instalar

### Uso pessoal (todos os seus projetos)

```bash
claude plugin marketplace add ~/projects/oraex-claude-plugins   # ou owner/repo do GitHub
claude plugin install oraex-security@oraex
```

Grava em `~/.claude/settings.json`. Vale em qualquer diretório.

### Por projeto (e para o time)

Em `.claude/settings.json` do projeto — versionado, não o `.local.json`:

```json
{
  "extraKnownMarketplaces": {
    "oraex": {
      "source": { "source": "github", "repo": "oraex/oraex-claude-plugins" }
    }
  },
  "enabledPlugins": { "oraex-security@oraex": true }
}
```

Quem clonar o repo recebe o plugin ao aceitar o diálogo de confiança do
workspace. Nada de copiar skill entre projetos.

> Fonte local (`{"source": "directory", "path": "/abs/path"}`) funciona só na
> sua máquina — o caminho absoluto não existe na do colega. Para o time, use
> `github`.

## Desenvolver

```bash
claude plugin validate ./plugins/oraex-security --strict   # manifesto do plugin
claude plugin validate . --strict                          # manifesto do marketplace
claude plugin details oraex-security@oraex                 # inventário + custo em tokens
```

Com o marketplace apontando para o **diretório local**, editar um `SKILL.md` e
rodar `/reload-plugins` reflete na sessão — sem reinstalar. Já com o marketplace
via **git** (o caso do time), uma mudança só propaga com **bump de versão +
`marketplace update` + `/reload-plugins`** — ver [Versionamento](#versionamento).

### Anatomia

```
oraex-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json          # catálogo: quais plugins existem e onde
└── plugins/
    └── oraex-security/
        ├── .claude-plugin/
        │   └── plugin.json       # manifesto: nome, versão, onde estão as skills
        └── skills/
            └── audit-mfa/
                └── SKILL.md      # a skill em si
```

Regra que mais gera erro: `.claude-plugin/` contém **apenas** o manifesto.
`skills/`, `agents/`, `hooks/` ficam na **raiz do plugin**, fora dela.

### Versionamento

`version` no `plugin.json` controla a atualização, e **o cache extraído é
indexado por versão**: enquanto o número não sobe, nem `marketplace update` nem
`/reload-plugins` re-extraem — a skill ativa continua a antiga, mesmo com o repo
já atualizado. Por isso, **todo edit de conteúdo (skill, template, reference)
exige subir a `version`** (`marketplace.json` não pina versão — só o `plugin.json`).

Para propagar uma mudança:

1. Suba a versão em `plugins/<plugin>/.claude-plugin/plugin.json`.
2. `git commit` + `push`.
3. Em cada máquina, **nesta ordem**:
   1. `claude plugin marketplace update oraex` — atualiza o clone do repo (**primeiro**).
   2. `/reload-plugins`, dentro do Claude Code — re-extrai e recarrega (**depois**).

A ordem importa: reload sem update relê o clone antigo; update sem reload não
recarrega a sessão. Para conferir que pegou (não presuma), veja o dir da versão
nova no cache: `~/.claude/plugins/cache/oraex/<plugin>/<versão>/`.

## Escrever uma skill nova

```bash
claude plugin init <nome> --with skills    # scaffold canônico
```

O que importa no `SKILL.md`:

- **`description` é o gatilho.** É por ela que o Claude decide carregar a
  skill sozinho. Escreva *quando* usar, com os termos que alguém usaria de
  verdade — não o que a skill faz por dentro. É o campo que separa uma skill
  que dispara sozinha de uma que só funciona se você digitar `/nome`.
- **Custo.** Só a `description` fica sempre em contexto (~240 tokens); o
  corpo só é lido quando dispara. Escreva à vontade no corpo.
- **`disallowed-tools`** para skills que não devem escrever (auditoria,
  revisão). Barreira real, não instrução no texto.
