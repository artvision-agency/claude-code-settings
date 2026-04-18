#!/bin/bash
set -euo pipefail
# Cron-скрипт: скриншот каждые 30 минут если таймер активен
TIMER_FILE="$HOME/.claude/timer/current.json"

if [ ! -f "$TIMER_FILE" ]; then
    exit 0
fi

# Проверяем что не на паузе
is_paused=$(python3 -c "import json; print(json.load(open('$TIMER_FILE')).get('is_paused', False))" 2>/dev/null || echo "True")
if [ "$is_paused" = "True" ]; then
    exit 0
fi

# Делаем скриншот
"$HOME/.claude/scripts/task-timer.sh" screenshot
