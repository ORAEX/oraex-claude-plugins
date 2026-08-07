#!/usr/bin/env bash
# session.sh — diagnóstico de sessão do oraex-claude-plugins (marketplace de plugins).
# Consumido pela skill oraex-baseline:sessao. Este repo não tem deps/DB/env, então os
# checks relevantes são: git + validação de plugin + guarda de bump de versão.
set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 1

info(){ printf '  %s\n' "$*"; }
warn(){ printf '  ! %s\n' "$*"; }

check_git(){
  git fetch --quiet 2>/dev/null || warn "git fetch falhou (offline?)"
  local up counts ahead behind
  up=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) \
    || { warn "branch sem upstream"; return; }
  counts=$(git rev-list --left-right --count "HEAD...$up" 2>/dev/null) || return
  ahead=${counts%%[[:space:]]*}; behind=${counts##*[[:space:]]}
  [ "$behind" -gt 0 ] && warn "atrás do remoto em $behind commit(s) -> git pull --ff-only"
  [ "$ahead" -gt 0 ]  && warn "à frente em $ahead commit(s) sem push"
  if [ -n "$(git status --porcelain)" ]; then warn "working tree suja:"; git status --short; fi
  [ "$behind" = 0 ] && [ "$ahead" = 0 ] && [ -z "$(git status --porcelain)" ] && info "git ok"
}

validate_plugins(){
  claude plugin validate . --strict >/dev/null 2>&1 \
    && info "marketplace ok" \
    || warn "marketplace INVÁLIDO -> claude plugin validate . --strict"
  local p
  for p in plugins/*/; do
    [ -d "$p" ] || continue
    claude plugin validate "$p" --strict >/dev/null 2>&1 \
      && info "plugin ok: ${p%/}" \
      || warn "plugin INVÁLIDO: ${p%/} -> claude plugin validate $p --strict"
  done
  local f
  for f in $(find plugins -path '*/templates/*.sh' 2>/dev/null) scripts/*.sh; do
    [ -f "$f" ] || continue
    bash -n "$f" 2>/dev/null && info "sh ok: $f" || warn "sh com erro de sintaxe: $f"
  done
}

# Guarda de bump: conteúdo de plugin mudou vs origin/main sem subir a version?
bump_guard(){
  git fetch --quiet 2>/dev/null || true
  local p
  for p in plugins/*/; do
    [ -d "$p" ] || continue
    git diff --quiet origin/main -- "$p" 2>/dev/null && continue  # sem mudança vs origin
    if git diff origin/main -- "${p}.claude-plugin/plugin.json" 2>/dev/null | grep -q '^[+-].*"version"'; then
      info "bump ok: ${p%/} (version mudou vs origin)"
    else
      warn "BUMP FALTANDO: ${p%/} mudou vs origin/main mas a version do plugin.json NÃO subiu"
    fi
  done
}

case "${1:-}" in
  start)
    echo "== abrindo sessão =="
    check_git
    echo "== leia o PROJECT_STATE.md antes de retomar ==" ;;
  end)
    echo "== encerrando sessão =="
    check_git
    echo "-- validação (marketplace + plugins + templates) --"; validate_plugins
    echo "-- guarda de bump de versão --"; bump_guard
    echo "== atualize o PROJECT_STATE.md com o que mudou ==" ;;
  *)
    echo "uso: $0 {start|end}"; exit 2 ;;
esac
