#!/usr/bin/env bash
# session.sh — diagnóstico de sessão (padrão ORAEX / skill sessao).
# Versionado: roda igual em toda máquina sincronizada por git.
# Universal (já implementado): git, runtime, env. Específico do stack: blocos <projeto>.
set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 1

# Arquivos de ambiente que NÃO viajam no git e são obrigatórios (separados por espaço):
REQUIRED_ENV_FILES=".env.local"

info(){ printf '  %s\n' "$*"; }
warn(){ printf '  ! %s\n' "$*"; }

check_git(){
  git fetch --quiet 2>/dev/null || warn "git fetch falhou (offline?)"
  local up; up=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) \
    || { warn "branch sem upstream"; return; }
  local counts ahead behind
  counts=$(git rev-list --left-right --count "HEAD...$up" 2>/dev/null) || return
  ahead=${counts%%[[:space:]]*}; behind=${counts##*[[:space:]]}
  [ "$behind" -gt 0 ] && warn "atrás do remoto em $behind commit(s) -> git pull --ff-only"
  [ "$ahead" -gt 0 ]  && warn "à frente em $ahead commit(s) sem push"
  if [ -n "$(git status --porcelain)" ]; then warn "working tree suja:"; git status --short; fi
  [ "$behind" = 0 ] && [ "$ahead" = 0 ] && [ -z "$(git status --porcelain)" ] && info "git ok"
}

check_runtime(){
  if [ -f .nvmrc ]; then
    local want have; want=$(cat .nvmrc); have=$(node -v 2>/dev/null || echo "?")
    case "$have" in
      *"${want#v}"*) info "node $have ok" ;;
      *) warn "node $have != .nvmrc $want -> rode no seu shell: ! nvm use" ;;
    esac
  fi
  # <projeto>: outras versões de runtime (.tool-versions, python, etc.)
}

check_env(){
  local f
  for f in $REQUIRED_ENV_FILES; do
    if [ -f "$f" ]; then info "env ok: $f"
    else warn "FALTA $f (gitignored; traga da outra máquina ou do cofre via .envrc)"; fi
  done
}

check_deps(){
  # <projeto>: verifique deps vs lockfile e instale respeitando o lockfile.
  #   ex.: npm ci  |  pnpm i --frozen-lockfile  |  uv sync
  #   NUNCA use comando que altera o lockfile (npm install, npm audit fix).
  warn "check_deps: implemente para o stack deste projeto"
}

check_services(){
  : # <projeto>: serviços locais (banco, etc.) + migrations pendentes (local e remoto).
    #   Prefira migration incremental (preserva dados) a reset total.
}

run_ci(){
  # <projeto>: os MESMOS checks do CI (lint, typecheck, testes) — o que a outra máquina puxa.
  #   ex.: npm run check && npm run typecheck
  warn "run_ci: implemente para o stack deste projeto"
}

case "${1:-}" in
  start)
    echo "== abrindo sessão =="
    check_git; check_runtime; check_env; check_deps; check_services
    echo "== leia o PROJECT_STATE.md antes de retomar ==" ;;
  end)
    echo "== encerrando sessão =="
    check_git; run_ci
    echo "== atualize o PROJECT_STATE.md com o que mudou ==" ;;
  *)
    echo "uso: $0 {start|end}"; exit 2 ;;
esac
