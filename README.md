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

Com o marketplace apontando para o diretório local, editar um `SKILL.md` e
rodar `/reload-plugins` já reflete na sessão — sem reinstalar.

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

`version` no `plugin.json` controla a atualização: quem instalou só recebe
novidade quando o número sobe. Suba a versão ao mudar uma skill, senão o
time continua com a antiga.

```bash
claude plugin update oraex-security@oraex
```

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
