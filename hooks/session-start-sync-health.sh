#!/bin/bash
# session-start-sync-health.sh — быстрый детект branch-drift синк-репо на старте сессии.
# Урок 2026-06-11 (AUTO CTX 50): ~/.claude сидел на боковой ветке context-diet-w1 →
# правки уезжали мимо main, другие машины их не видели; заметили случайно.
# Warn-only, без сети (branch — мгновенно; behind — по последним известным origin-refs,
# свежесть refs обеспечивают существующие SessionStart pull-хуки).
# Bypass: SYNC_HEALTH_OFF=1. Полная проверка с fetch+VPS: ~/.claude/scripts/sync-health.sh --vps
set -uo pipefail
[ "${SYNC_HEALTH_OFF:-0}" = "1" ] && exit 0

OUT=""
check() {
  local path="$1" expected="$2"
  [ -d "$path/.git" ] || return 0
  local br behind
  br=$(git -C "$path" branch --show-current 2>/dev/null) || return 0
  if [ -n "$br" ] && [ "$br" != "$expected" ]; then
    OUT+="  ⚠️ $path на ветке '$br' (ожидается '$expected') — коммиты уезжают мимо main, другие машины их НЕ видят. Фикс: git -C $path checkout $expected && git -C $path pull"$'\n'
  fi
  behind=$(git -C "$path" rev-list --count HEAD..origin/"$br" 2>/dev/null || echo 0)
  if [ "${behind:-0}" -gt 20 ] 2>/dev/null; then
    OUT+="  🔴 $path отстаёт от origin/$br на $behind коммитов — git pull"$'\n'
  fi
  return 0
}

check "$HOME/.claude" main
check "$HOME/artvision-data" main
check "$HOME/devops-agent" main

if [ -n "$OUT" ]; then
  printf '═══ SYNC-HEALTH (branch-drift) ═══\n%s  Полная проверка: ~/.claude/scripts/sync-health.sh --vps\n' "$OUT"
fi
exit 0
