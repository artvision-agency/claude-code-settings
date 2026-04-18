#!/bin/bash
# Запуск Claude Code сессий в отдельных tmux-окнах
# Каждая сессия = отдельный процесс, закрытие одной НЕ убивает остальные
# Использование: claude-sessions-launcher.sh [session-name]
# Без аргументов — показать меню

set -euo pipefail

TMUX_SESSION="claude"

# Создать tmux-сессию если не существует
SESSION_CREATED=false
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    tmux new-session -d -s "$TMUX_SESSION" -n "_init"
    SESSION_CREATED=true
    echo "Created tmux session: $TMUX_SESSION"
fi

launch_claude() {
    local name="$1"
    local dir="$2"

    # Проверяем нет ли уже такого окна
    if tmux list-windows -t "$TMUX_SESSION" -F '#{window_name}' 2>/dev/null | grep -q "^${name}$"; then
        # Проверяем запущен ли claude в этом окне
        local pane_cmd
        pane_cmd=$(tmux list-panes -t "$TMUX_SESSION:$name" -F '#{pane_current_command}' 2>/dev/null | head -1)
        if echo "$pane_cmd" | grep -qi "claude"; then
            echo "Window '$name' already running claude. Switching..."
            tmux select-window -t "$TMUX_SESSION:$name"
        else
            echo "Window '$name' exists but claude not running. Restarting..."
            tmux send-keys -t "$TMUX_SESSION:$name" "cd '$dir' && claude" Enter
        fi
    else
        tmux new-window -t "$TMUX_SESSION" -n "$name" "cd '$dir' && claude"
        echo "Launched: $name (in $dir)"
    fi
}

# Удалить временное окно _init после запуска первого реального окна
cleanup_init_window() {
    if [ "$SESSION_CREATED" = true ]; then
        tmux kill-window -t "$TMUX_SESSION:_init" 2>/dev/null || true
    fi
}

if [ $# -eq 0 ]; then
    echo "═══════════════════════════════════════"
    echo "  Claude Sessions Launcher (tmux)"
    echo "═══════════════════════════════════════"
    echo ""
    echo "  1) ops       — ~/artvision-data"
    echo "  2) bot       — ~/artvision-tg-bot"
    echo "  3) devops    — ~/devops-agent"
    echo "  4) all       — запустить все 3"
    echo "  5) attach    — подключиться к tmux"
    echo ""
    read -p "  Выбор: " choice

    case "$choice" in
        1|ops)     launch_claude "ops" "$HOME/artvision-data"; cleanup_init_window ;;
        2|bot)     launch_claude "bot" "$HOME/artvision-tg-bot"; cleanup_init_window ;;
        3|devops)  launch_claude "devops" "$HOME/devops-agent"; cleanup_init_window ;;
        4|all)
            launch_claude "ops" "$HOME/artvision-data"
            launch_claude "bot" "$HOME/artvision-tg-bot"
            launch_claude "devops" "$HOME/devops-agent"
            cleanup_init_window
            echo ""
            echo "All 3 sessions launched. Attaching..."
            sleep 1
            tmux attach-session -t "$TMUX_SESSION"
            ;;
        5|attach)  tmux attach-session -t "$TMUX_SESSION" ;;
        *)         echo "Unknown: $choice" ;;
    esac
else
    case "$1" in
        ops)     launch_claude "ops" "$HOME/artvision-data"; cleanup_init_window ;;
        bot)     launch_claude "bot" "$HOME/artvision-tg-bot"; cleanup_init_window ;;
        devops)  launch_claude "devops" "$HOME/devops-agent"; cleanup_init_window ;;
        all)
            launch_claude "ops" "$HOME/artvision-data"
            launch_claude "bot" "$HOME/artvision-tg-bot"
            launch_claude "devops" "$HOME/devops-agent"
            cleanup_init_window
            echo "All 3 sessions launched."
            echo "Run: tmux attach -t claude"
            ;;
        attach)  tmux attach-session -t "$TMUX_SESSION" ;;
        *)       echo "Unknown session: $1. Use: ops|bot|devops|all|attach" ;;
    esac
fi
