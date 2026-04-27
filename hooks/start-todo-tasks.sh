#!/usr/bin/env bash
# start-todo-tasks.sh — SessionStart hook.
# Инжектит top-5 priority:high задач ТОЛЬКО из TODO текущего контекста сессии.
#
# Контекст определяется через ~/.claude/scripts/lib/todo-route.sh (cwd → ctx).
# Если cwd=$HOME (нет явной сессии) → silent exit, top не инжектится.
# Цель: минимальный контекст, максимальный сигнал. Детали — в TODO файлах.
# История:
#   - до 2026-04-22 — top-31 (5h+3o × 5 files), ~5KB на старте
#   - до 2026-04-27 — top-5 со ВСЕХ 5 TODO (ops+bot+infra+presale+products)
#   - после 2026-04-27 — top-5 ТОЛЬКО текущего контекста (фильтр по cwd)

set -uo pipefail

LIB="${HOME}/.claude/scripts/lib/todo-route.sh"
[ -f "$LIB" ] || { echo '{}'; exit 0; }
# shellcheck source=/dev/null
source "$LIB"

mapping="$(todo_for_cwd "${PWD:-$HOME}")"
TODO="${mapping%%$'\t'*}"
CTX="${mapping##*$'\t'}"

# home / нет TODO → silent (не пинаем top на нейтральной сессии)
[ "$CTX" = "home" ] && { echo '{}'; exit 0; }
[ -f "$TODO" ] || { echo '{}'; exit 0; }

TOTAL=$(grep -c '^- \[ \]' "$TODO" 2>/dev/null || echo 0)
TOP_HIGH=$(grep '^- \[ \].*priority:high' "$TODO" 2>/dev/null | head -5)

if [ -z "$TOP_HIGH" ]; then
  echo '{}'
  exit 0
fi

COUNT=$(printf '%s\n' "$TOP_HIGH" | grep -c '^-' || echo 0)

jq -n --arg pending "$TOP_HIGH" --arg count "$COUNT" --arg total "$TOTAL" --arg ctx "$CTX" '
{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: (
      "📋 TOP-" + $count + " priority:high (контекст: " + $ctx + ", из " + $total + " pending в этом TODO):\n" +
      $pending +
      "\nПолный список: TODO.md контекста " + $ctx + ". Меню: 1 Комбайн / 2 Интервью / 3 Обзор / 4 Синк / 5 Фикс."
    )
  }
}
'
