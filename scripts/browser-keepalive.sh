#!/bin/bash
# Browser Keepalive — предотвращает дисконнект Chrome for Testing
#
# Запуск: ~/.claude/scripts/browser-keepalive.sh &
# Стоп:   kill $(cat /tmp/browser-keepalive.pid)
#
# Что делает:
# 1. Каждые 30 сек проверяет что Chrome for Testing жив
# 2. Если процесс упал — убивает зомби и чистит lock-файлы
# 3. Логирует в /tmp/browser-keepalive.log

LOG="/tmp/browser-keepalive.log"
PIDFILE="/tmp/browser-keepalive.pid"
CHROME_DIR="$HOME/Library/Application Support/Google/Chrome for Testing"
INTERVAL=30

# Записать свой PID
echo $$ > "$PIDFILE"
echo "[$(date)] Browser keepalive started (PID $$)" >> "$LOG"

cleanup() {
    echo "[$(date)] Browser keepalive stopped" >> "$LOG"
    rm -f "$PIDFILE"
    exit 0
}
trap cleanup EXIT INT TERM

while true; do
    # Проверить наличие Chrome for Testing процесса
    CHROME_PID=$(pgrep -f "Chrome for Testing" | head -1)

    if [ -z "$CHROME_PID" ]; then
        echo "[$(date)] WARN: Chrome for Testing not running" >> "$LOG"
    else
        # Проверить что процесс отвечает (не зомби)
        if kill -0 "$CHROME_PID" 2>/dev/null; then
            # Всё ок, Chrome жив
            :
        else
            echo "[$(date)] ERROR: Chrome for Testing zombie detected (PID $CHROME_PID)" >> "$LOG"

            # Убить все процессы Chrome for Testing
            pkill -9 -f "Chrome for Testing" 2>/dev/null

            # Очистить lock-файлы
            rm -f "$CHROME_DIR/SingletonLock" 2>/dev/null
            rm -f "$CHROME_DIR/SingletonSocket" 2>/dev/null
            rm -f "$CHROME_DIR/SingletonCookie" 2>/dev/null

            echo "[$(date)] Cleaned up zombie Chrome processes and lock files" >> "$LOG"
        fi
    fi

    # Проверить наличие битых lock-файлов без живого Chrome
    if [ -z "$CHROME_PID" ] && [ -f "$CHROME_DIR/SingletonLock" ]; then
        echo "[$(date)] WARN: Stale SingletonLock found without Chrome process, removing" >> "$LOG"
        rm -f "$CHROME_DIR/SingletonLock" 2>/dev/null
        rm -f "$CHROME_DIR/SingletonSocket" 2>/dev/null
        rm -f "$CHROME_DIR/SingletonCookie" 2>/dev/null
    fi

    sleep "$INTERVAL"
done
