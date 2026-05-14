#!/usr/bin/env bash
# bootstrap-mac-login.sh — открывает iTerm с Claude в ~/artvision-data при логине Mac.
# Вызывается LaunchAgent pro.artvision.bootstrap (RunAtLoad=true).
#
# Что делает:
#   1. Ждёт 15 сек чтобы Mac полностью загрузился (сеть, mounted volumes)
#   2. Открывает iTerm локально с Claude в ~/artvision-data
#   3. Через 60 сек (внутри iTerm — пользователь видит инструкцию) можно вручную набрать /go
#
# НЕ открывает VPS-окно автоматически — вызывается командой `claude-vps` вручную.

set -euo pipefail

LOG="$HOME/Library/Logs/artvision-bootstrap.log"
exec >> "$LOG" 2>&1

echo "=== bootstrap $(date '+%Y-%m-%d %H:%M:%S') ==="

# 1. Ждём загрузки системы
sleep 15

# 2. Проверяем что iTerm установлен
if ! [ -d "/Applications/iTerm.app" ]; then
    echo "ERROR: iTerm.app не найден, fallback на Terminal.app"
    USE_APP="Terminal"
else
    USE_APP="iTerm"
fi

# 3. Открываем терминал и запускаем claude в ~/artvision-data
if [ "$USE_APP" = "iTerm" ]; then
    osascript <<'AS'
tell application "iTerm"
    activate
    if (count of windows) = 0 then
        create window with default profile
    else
        tell current window to create tab with default profile
    end if
    tell current session of current window
        write text "cd ~/artvision-data && echo '🌅 Bootstrap session. Через 60 сек можешь набрать /go или сразу любую команду.' && claude"
    end tell
end tell
AS
else
    osascript <<'AS'
tell application "Terminal"
    activate
    do script "cd ~/artvision-data && claude"
end tell
AS
fi

echo "bootstrap launched $USE_APP at $(date '+%H:%M:%S')"
