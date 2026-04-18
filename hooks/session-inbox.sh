#!/bin/bash
# SessionStart hook: проверяет inbox для текущей сессии
# Если есть routed задачи — показывает уведомление

set -euo pipefail

CONFIG="$HOME/.claude/task-router/sessions.yaml"
INBOX_DIR="$HOME/.claude/task-router/inbox"
CWD="$(pwd)"

# Определяем имя сессии по cwd
SESSION_NAME=""

if command -v python3 &>/dev/null && [ -f "$CONFIG" ]; then
    SESSION_NAME=$(python3 - "$CONFIG" "$CWD" << 'PYEOF'
import yaml, os, sys
config_path = sys.argv[1]
cwd = sys.argv[2]
with open(config_path) as f:
    config = yaml.safe_load(f)
for name, sess in config.get("sessions", {}).items():
    if sess.get("cwd", "") == cwd:
        print(name)
        break
PYEOF
)
fi

if [ -z "$SESSION_NAME" ]; then
    exit 0
fi

INBOX="$INBOX_DIR/$SESSION_NAME.md"

if [ -f "$INBOX" ] && [ -s "$INBOX" ]; then
    COUNT=$(grep -c '^\- \[' "$INBOX" 2>/dev/null || echo "0")
    if [ "$COUNT" -gt 0 ] 2>/dev/null; then
        # Экранируем JSON-спецсимволы в тексте задач
        MSG=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    text = f.read()
# json.dumps экранирует кавычки, бэкслеши, переносы строк
print(json.dumps(text)[1:-1])  # убираем внешние кавычки от dumps
" "$INBOX")
        # Очищаем inbox ПОСЛЕ успешного чтения (truncate, не echo)
        : > "$INBOX"
        echo "{\"systemMessage\": \"$COUNT задач перемещено в эту сессию роутером:\\n$MSG\"}"
    fi
fi
