#!/bin/bash
# sync-health.sh — детект branch-drift и отставания синк-репо (урок 2026-06-11 AUTO CTX 50:
# ~/.claude сидел на боковой ветке context-diet-w1 → правки не доходили до main/других машин;
# VPS root/.claude отстал на 113 коммитов и никто не заметил).
# Использование: sync-health.sh [--vps]  (exit 0 = всё ок, exit 1 = есть проблемы)
set -uo pipefail

FAIL=0
check_repo() {
  local path="$1" expected_branch="$2"
  [ -d "$path/.git" ] || { echo "🔴 $path — не git-репо"; FAIL=1; return; }
  local br behind ahead
  br=$(git -C "$path" branch --show-current)
  git -C "$path" fetch origin -q 2>/dev/null
  behind=$(git -C "$path" rev-list --count HEAD..origin/"$br" 2>/dev/null || echo "?")
  ahead=$(git -C "$path" rev-list --count origin/"$br"..HEAD 2>/dev/null || echo "?")
  local mark="✅"
  [ "$br" != "$expected_branch" ] && { mark="⚠️ ВЕТКА $br≠$expected_branch (split-brain: коммиты мимо main)"; FAIL=1; }
  [ "$behind" != "0" ] && [ "$behind" != "?" ] && { mark="🔴 ОТСТАЁТ на $behind"; FAIL=1; }
  echo "$mark $path [$br] behind=$behind ahead=$ahead"
}

echo "═══ SYNC-HEALTH $(date '+%Y-%m-%d %H:%M') ═══"
check_repo "$HOME/.claude" main
check_repo "$HOME/artvision-data" main
check_repo "$HOME/artvision-tg-bot" "$(git -C "$HOME/artvision-tg-bot" branch --show-current 2>/dev/null || echo main)"
check_repo "$HOME/devops-agent" main

if [ "${1:-}" = "--vps" ]; then
  echo "--- VPS 80.90.181.152 ---"
  ssh -o ConnectTimeout=8 root@80.90.181.152 '
    for D in /root/.claude /root/artvision-data; do
      BR=$(git -C $D branch --show-current 2>/dev/null)
      git -C $D fetch origin -q 2>/dev/null
      BEHIND=$(git -C $D rev-list --count HEAD..origin/$BR 2>/dev/null || echo "?")
      echo "$D [$BR] behind=$BEHIND"
    done' 2>/dev/null || { echo "🔴 VPS недоступен"; FAIL=1; }
fi

[ "$FAIL" = "0" ] && echo "✅ Все репо на ожидаемых ветках и не отстают" || echo "⚠️ Есть проблемы — чинить: git checkout main && git pull (бэкап-ветка если есть локальные коммиты)"
exit $FAIL
