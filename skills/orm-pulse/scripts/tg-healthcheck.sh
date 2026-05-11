#!/bin/bash
# P0-2 TG healthcheck — детектит silent TG failures в orm-pulse логах.
# Запускать cron'ом каждые 6h.
#
# Прецедент: 09.05.2026 curl_rc=35 SSL_ERROR_SYSCALL → daily-summary потерян молча.
# QA-2 (commit 252e11aa0).

set -uo pipefail
PATH="/usr/bin:/bin:/usr/sbin:/sbin"

STATE_DIR="${HOME}/.claude/state/orm-pulse"
mkdir -p "$STATE_DIR"
RATE_LIMIT_FILE="$STATE_DIR/tg-healthcheck-last"
RATE_LIMIT_HOURS=6
LOG_GLOB="${HOME}/.claude/logs/orm-*.err"

# Окно: 24h назад
WINDOW_HOURS=24
CUTOFF=$(date -u -v-${WINDOW_HOURS}H +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u -d "${WINDOW_HOURS} hours ago" +"%Y-%m-%d %H:%M:%S")

# Паттерны failure (escape для grep)
PATTERN='curl_rc=35|SSL_ERROR|Send failed|❌ Send|TG.*failed|tg-send failed|Network error|getaddrinfo failed'

# Файлы изменённые за последние WINDOW_HOURS
FRESH_ERRS=$(find ~/.claude/logs/ -name "orm-*.err" -mtime -1 2>/dev/null)
if [ -z "$FRESH_ERRS" ]; then
    echo "ℹ️ Нет свежих .err за ${WINDOW_HOURS}h — TG infra жив (предположительно)"
    exit 0
fi

# Считаем совпадения
# grep -c возвращает 1 если 0 матчей в файле — поэтому 2>/dev/null + awk-сумма
COUNT=$(echo "$FRESH_ERRS" | xargs grep -hcE "$PATTERN" 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
COUNT=${COUNT:-0}

if [ "$COUNT" -eq 0 ]; then
    echo "✅ TG infra жив — 0 fail за ${WINDOW_HOURS}h"
    exit 0
fi

echo "⚠️ Найдено $COUNT TG-failure паттернов за ${WINDOW_HOURS}h"
echo "$FRESH_ERRS" | xargs grep -El "$PATTERN" 2>/dev/null | head -5

# Rate-limit
NOW_TS=$(date +%s)
if [ -f "$RATE_LIMIT_FILE" ]; then
    LAST_ALERT_TS=$(cat "$RATE_LIMIT_FILE")
    AGE=$((NOW_TS - LAST_ALERT_TS))
    if [ "$AGE" -lt $((RATE_LIMIT_HOURS * 3600)) ]; then
        echo "⏸ Rate-limit — последний алёрт ${AGE}s назад"
        exit 0
    fi
fi

# Список затронутых сервисов (краткий)
AFFECTED=$(echo "$FRESH_ERRS" | xargs grep -El "$PATTERN" 2>/dev/null | xargs -n1 basename | sed 's/\.err//' | sort -u | tr '\n' ',' | sed 's/,$//')

MSG="🚨 TG infra: $COUNT silent failures за ${WINDOW_HOURS}h
Affected: $AFFECTED
Проверь: grep -E '$PATTERN' ~/.claude/logs/orm-*.err
Last few:
$(echo "$FRESH_ERRS" | xargs grep -hE "$PATTERN" 2>/dev/null | tail -3)"

if [ -x "$HOME/.claude/scripts/tg-send.sh" ]; then
    "$HOME/.claude/scripts/tg-send.sh" team "$MSG" || echo "❌ ОЧЕНЬ ПЛОХО: tg-send тоже упал"
fi

echo "$NOW_TS" > "$RATE_LIMIT_FILE"
echo "🚨 Алёрт отправлен в TG team"
