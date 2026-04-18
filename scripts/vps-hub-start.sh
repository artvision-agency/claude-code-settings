#!/bin/bash
set -euo pipefail
# Запуск HUB-сессии на VPS в tmux
# Использование: ssh vps && bash ~/.claude/scripts/vps-hub-start.sh

export BUN_INSTALL="/root/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

SESSION_NAME="claude-hub"

# Проверяем есть ли уже сессия
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "HUB уже запущен. Подключиться: tmux attach -t $SESSION_NAME"
    exit 0
fi

# Запускаем claude в tmux
tmux new-session -d -s "$SESSION_NAME" \
    "claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official --continue"

echo "HUB запущен в tmux сессии '$SESSION_NAME'"
echo "Подключиться: tmux attach -t $SESSION_NAME"
echo "Отключиться без остановки: Ctrl+B, затем D"
