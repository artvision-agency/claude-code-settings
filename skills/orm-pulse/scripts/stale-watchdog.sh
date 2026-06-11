#!/bin/bash
# Q11 stale-watchdog — алёрт в TG если дашборд не обновлялся >2ч.
# Запускать cron'ом раз в час.
# Usage: stale-watchdog.sh <client>

set -euo pipefail
PATH="/usr/bin:/bin:/usr/sbin:/sbin"

CLIENT="${1:-blumart}"
DASHBOARD_URL="https://artvision.pro/orm-command-center/${CLIENT}.html"
THRESHOLD_HOURS="${STALE_THRESHOLD_HOURS:-2}"
RATE_LIMIT_FILE="${HOME}/.claude/state/orm-pulse/stale-watchdog-${CLIENT}-last-alert"
RATE_LIMIT_HOURS=6

# basic auth для дашборда (из tokens.json)
TOKENS="/Users/antonk/artvision-data/tokens.json"
DASHBOARD_AUTH="${ORM_DASHBOARD_AUTH:-$(/usr/bin/python3 -c "import json; d=json.load(open('$TOKENS')); print(d.get('artvision_pro',{}).get('dashboard_basic_auth','admin:111'))" 2>/dev/null)}"

LAST_MOD=$(curl -sI -u "$DASHBOARD_AUTH" "$DASHBOARD_URL" -m 10 2>/dev/null | grep -i 'last-modified' | sed 's/[Ll]ast-[Mm]odified: //;s/\r//')

if [ -z "$LAST_MOD" ]; then
    echo "❌ Не удалось прочитать Last-Modified для $DASHBOARD_URL"
    exit 1
fi

# macOS: -u flag заставляет date интерпретировать вход как UTC (иначе считает MSK → ошибка +3h)
LAST_MOD_TS=$(date -ju -f "%a, %d %b %Y %H:%M:%S GMT" "$LAST_MOD" "+%s" 2>/dev/null || date -u -d "$LAST_MOD" "+%s" 2>/dev/null || echo 0)
NOW_TS=$(date "+%s")
AGE_SEC=$((NOW_TS - LAST_MOD_TS))
AGE_HOURS=$((AGE_SEC / 3600))

echo "Dashboard age: ${AGE_HOURS}h (threshold: ${THRESHOLD_HOURS}h)"

if [ "$AGE_HOURS" -lt "$THRESHOLD_HOURS" ]; then
    echo "✅ Свежий — алёрт не нужен"
    exit 0
fi

# Rate-limit: не чаще RATE_LIMIT_HOURS
if [ -f "$RATE_LIMIT_FILE" ]; then
    LAST_ALERT_TS=$(cat "$RATE_LIMIT_FILE")
    AGE_ALERT_SEC=$((NOW_TS - LAST_ALERT_TS))
    if [ "$AGE_ALERT_SEC" -lt $((RATE_LIMIT_HOURS * 3600)) ]; then
        echo "⏸ Rate-limit — последний алёрт ${AGE_ALERT_SEC}s назад"
        exit 0
    fi
fi

# Отправляем алёрт
MSG="🚨 ${CLIENT} Command Center stale: ${AGE_HOURS}ч с последнего refresh (порог ${THRESHOLD_HOURS}ч)
URL: ${DASHBOARD_URL}
Last-Modified: ${LAST_MOD}
Проверь: launchctl list pro.artvision.orm-pulse.${CLIENT}-refresh"

if [ -x "$HOME/.claude/scripts/tg-send.sh" ]; then
    NOTIFY_FORCE=1 "$HOME/.claude/scripts/tg-send.sh" team "$MSG" || echo "tg-send failed"
fi

mkdir -p ${HOME}/.claude/state/orm-pulse
echo "$NOW_TS" > "$RATE_LIMIT_FILE"
echo "🚨 Алёрт отправлен"
