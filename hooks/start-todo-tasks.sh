#!/usr/bin/env bash
# start-todo-tasks.sh — SessionStart hook.
# Инжектит top-5 priority:high задач (total, не per-file) из всех TODO.md.
#
# Цель: минимальный контекст, максимальный сигнал. Детали — в TODO файлах.
# История: до 2026-04-22 инжектил top-31 (5h+3o × 5 files) → жрал ~5KB на старте.

set -uo pipefail

TODO_FILES=(
  "$HOME/artvision-data/TODO.md"
  "$HOME/artvision-data/presale/TODO.md"
  "$HOME/artvision-data/products/TODO.md"
  "$HOME/artvision-tg-bot/TODO.md"
  "$HOME/devops-agent/TODO.md"
)

# Глобальный счётчик pending (для контекста "5 из N")
TOTAL=0
for f in "${TODO_FILES[@]}"; do
  [ -f "$f" ] || continue
  FILE_TOTAL=$(grep -c '^- \[ \]' "$f" 2>/dev/null || echo 0)
  TOTAL=$((TOTAL + FILE_TOTAL))
done

# Собираем все priority:high со всех файлов, берём top-5 (глобально)
TOP_HIGH=""
while IFS= read -r line; do
  [ -n "$line" ] && TOP_HIGH+="$line"$'\n'
done < <(
  for f in "${TODO_FILES[@]}"; do
    [ -f "$f" ] || continue
    LABEL=$(echo "$f" | sed "s|$HOME/||" | sed 's|/TODO.md||')
    grep '^- \[ \].*priority:high' "$f" 2>/dev/null | sed "s|^- \[ \]|- [$LABEL]|"
  done | head -5
)

if [ -z "$TOP_HIGH" ]; then
  echo '{}'
  exit 0
fi

COUNT=$(echo -n "$TOP_HIGH" | grep -c '^-' || echo 0)

jq -n --arg pending "$TOP_HIGH" --arg count "$COUNT" --arg total "$TOTAL" '
{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: (
      "📋 TOP-" + $count + " priority:high (из " + $total + " pending total):\n" +
      $pending +
      "\nПолный список: TODO.md в контексте. Меню: 1 Комбайн / 2 Интервью / 3 Обзор / 4 Синк / 5 Фикс."
    )
  }
}
'
