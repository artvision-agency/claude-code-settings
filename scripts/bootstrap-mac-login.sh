#!/usr/bin/env bash
# bootstrap-mac-login.sh — открывает терминал с Claude в ~/artvision-data при логине Mac.
# Вызывается LaunchAgent pro.artvision.bootstrap (RunAtLoad=true).
#
# Приоритет терминалов: Ghostty > iTerm > Terminal.app
# (Антон использует Ghostty по умолчанию, fallback нужен для других машин)

set -euo pipefail

LOG="$HOME/Library/Logs/artvision-bootstrap.log"
exec >> "$LOG" 2>&1

echo "=== bootstrap $(date '+%Y-%m-%d %H:%M:%S') ==="

sleep 15

# Авто-комбайн: bootstrap-сессия сразу запускает прогон очереди задач (/combine).
# Интерактивно — окно видно, Ctrl-C перехватывает чтобы дать свою задачу.
CMD="cd ~/artvision-data && echo '🌅 Bootstrap — авто-комбайн стартует. Ctrl-C чтобы перехватить и дать свою задачу.' && claude '/combine'"

if [ -d "/Applications/Ghostty.app" ]; then
    # Ghostty: open -na открывает новое окно; --args передаёт shell command
    # Стандартный путь — open + osascript keystroke (Accessibility permission уже выдан)
    open -na "Ghostty.app"
    sleep 2
    osascript <<AS
tell application "Ghostty" to activate
delay 0.5
tell application "System Events"
    keystroke "$CMD"
    delay 0.3
    key code 36  -- Return
end tell
AS
    echo "bootstrap launched Ghostty at $(date '+%H:%M:%S')"
elif [ -d "/Applications/iTerm.app" ]; then
    osascript <<'AS'
tell application "iTerm"
    activate
    if (count of windows) = 0 then
        create window with default profile
    else
        tell current window to create tab with default profile
    end if
    tell current session of current window
        write text "cd ~/artvision-data && claude '/combine'"
    end tell
end tell
AS
    echo "bootstrap launched iTerm at $(date '+%H:%M:%S')"
else
    osascript <<AS
tell application "Terminal"
    activate
    do script "$CMD"
end tell
AS
    echo "bootstrap launched Terminal at $(date '+%H:%M:%S')"
fi
