#!/bin/bash
set -euo pipefail
# PostCompact: напоминание о pending items после сжатия контекста
# Выводит сохранённый контекст + pending задачи из TODO

CONTEXT_FILE="/Users/antonk/artvision-data/.claude_temp_scripts/compact_context.md"
REMINDERS=""

# 1. Напоминание о сохранённом контексте
if [ -f "$CONTEXT_FILE" ]; then
  REMINDERS="⚠️ ПОСЛЕ КОМПАКТИНГА: прочитай $CONTEXT_FILE для восстановления контекста."
fi

# 2. Pending задачи из TODO файлов
for todo in /Users/antonk/artvision-data/TODO.md /Users/antonk/artvision-tg-bot/TODO.md /Users/antonk/devops-agent/TODO.md; do
  if [ -f "$todo" ]; then
    COUNT=$(grep -c '^\- \[ \]' "$todo" 2>/dev/null || echo "0")
    COUNT=$(echo "$COUNT" | tr -d '[:space:]')
    if [ "$COUNT" != "" ] && [ "$COUNT" != "0" ]; then
      REMINDERS="$REMINDERS
📋 $(basename "$(dirname "$todo")"): $COUNT pending задач в TODO.md"
    fi
  fi
done

# 3. Обязательное действие
if [ -n "$REMINDERS" ]; then
  echo "$REMINDERS"
  echo ""
  echo "ОБЯЗАТЕЛЬНО: TaskCreate для каждого pending item. Не терять обещания."
fi

exit 0
