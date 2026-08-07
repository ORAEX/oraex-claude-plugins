---
name: sessao
description: Abre ou encerra uma sessão de trabalho num projeto sincronizado por git entre várias máquinas. Use ao começar ("bom dia", "vamos retomar", "abrindo sessão", "sentei na outra máquina") e ao terminar ("encerrando", "vou parar por hoje", "fechando a sessão"). Roda o scripts/session.sh do projeto e interpreta a saída, resolvendo divergência de git, dependências desatualizadas, arquivos de ambiente que não viajam, migrations pendentes (local e remoto) e os checks de CI antes de largar a máquina.
---

# Rotina de sessão (padrão ORAEX)

Para projetos tocados em **mais de uma máquina** sincronizadas por git. O que
quebra a troca de máquina quase nunca é o git em si — é o entorno: dependências
velhas, banco local sem a última migration, arquivo de ambiente que não viaja no
commit, commit local esquecido sem push.

O diagnóstico mora em **`scripts/session.sh`** (versionado, roda igual em toda
máquina). Sua função aqui é **rodar o script, interpretar a saída e resolver as
pendências** — não repetir as checagens na mão. Os checks universais (git,
runtime, env) já vêm no template; os específicos do stack (deps, serviços, CI)
o projeto preenche nos blocos marcados `<projeto>`.

Complementa as outras skills do baseline: `.env.local` segue [[env-conventions]];
MCPs de nuvem opt-in por sessão seguem [[mcp-baseline]].

## Abrindo a sessão

1. Rode `./scripts/session.sh start`.
2. Para **cada** pendência, **aja** em vez de só repassar:
   - **atrás do remoto** → `git pull --ff-only`.
   - **dependências desatualizadas** → o comando de install do projeto que
     **respeita o lockfile** (`npm ci`, `pnpm i --frozen-lockfile`, `uv sync`…).
     **Nunca** um que mexe no lockfile (`npm install`, `npm audit fix`).
   - **runtime fora do pino** (`.nvmrc`/`.tool-versions`) → avise; a troca
     (`nvm use` etc.) o usuário roda no shell dele (`! nvm use`), não via Bash.
   - **arquivo de ambiente que não viaja ausente** (ex.: `.env.local`) →
     **bloqueia**. É gitignored; vem da outra máquina (cópia manual) ou do cofre
     via `.envrc` (ver [[env-conventions]]). Peça para o usuário trazer.
   - **serviço local parado** (banco etc.) → suba-o.
   - **migrations pendentes no banco local** → aplique **incrementalmente**,
     preservando dados; reset total só como último recurso (e aí lembre da
     repopulação específica do projeto).
   - **working tree suja** → mostre o que é e **pergunte** se retoma ou descarta;
     pode ser trabalho interrompido na própria máquina.
3. Leia o `PROJECT_STATE.md` (se houver) e feche com um resumo curto: onde
   paramos, o que ficou pendente, qual o próximo passo.

## Encerrando a sessão

1. Rode `./scripts/session.sh end` (roda os checks de CI do projeto).
2. Se algum check falhou, **conserte antes de encerrar** — a outra máquina vai
   puxar esse commit.
3. Trabalho não commitado → proponha o commit com uma mensagem que descreva a mudança.
4. **Push exige OK explícito do usuário.** Commite à vontade; pare antes de
   pushar. Mas sem push a outra máquina não vê nada — então **pergunte**, não
   deixe passar.
5. Se a branch adiciona migrations, lembre que aplicar em staging/produção é
   ação **manual** do projeto (banco antes do código).
6. Ofereça atualizar o `PROJECT_STATE.md` com o que mudou — costuma ser o **único
   canal de contexto entre as máquinas** (não há histórico de conversa compartilhado).

## Instalar num projeto novo

1. Copie `templates/session.sh` para `scripts/session.sh` do projeto; `chmod +x`.
2. Preencha os blocos `<projeto>`: `check_deps`, `check_services`, `run_ci`, e a
   lista `REQUIRED_ENV_FILES` (os arquivos de ambiente que não viajam).
3. Commite o `scripts/session.sh` (é versionado — roda igual em toda máquina).
4. Garanta um `PROJECT_STATE.md` versionado como canal de contexto entre máquinas.

## O que NÃO fazer

- Não edite arquivo de ambiente que não viaja achando que vai propagar: é
  gitignored e por máquina.
- Não habilite MCPs de nuvem (`supabase-prd`/`supabase-stg` etc.) por padrão —
  opt-in por sessão via `/mcp` (`enabledMcpjsonServers`/`disabledMcpjsonServers`
  no `.claude/settings.json`). Ver [[mcp-baseline]].
- Não rode comando de install que altera o lockfile.
- Não jogue detalhe de stack **na skill**: ele mora no `session.sh` do projeto
  (blocos `<projeto>`), não aqui. Assim a skill vale igual para todo projeto.
