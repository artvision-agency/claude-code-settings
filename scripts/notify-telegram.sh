#!/bin/bash
# Отправка уведомлений в Telegram чат команды
# Использование: notify-telegram.sh "Текст сообщения"

BOT_TOKEN="8399522625:AAEEayoY1yjLEXM5Ys7jvlruYyoqKHGh1ho"
CHAT_ID="${TELEGRAM_TEAM_CHAT_ID:--4273200821}"  # Artvision team chat

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "Usage: notify-telegram.sh \"Message text\""
    exit 1
fi

# ── ФИЛЬТР ОШИБОК (Антон 25.05.2026): в TG идут только результаты работы ботов,
#    инфра/health/error-алерты — в лог, НЕ в чат. Bypass: NOTIFY_FORCE=1.
#    Прецедент: командный чат завален BOT CRITICAL/RESTART SPIKE/VPS UNREACHABLE.
if [ "${NOTIFY_FORCE:-0}" != "1" ]; then
    ERR_RE='BOT CRITICAL|RESTART SPIKE|restarts=|UNREACHABLE|RECOVERED|back online|API DOWN|API DEGRADED|kex_exchange|Connection closed|MaxStartups|🚨|💥|🆘|⛔|CRITICAL:|ALERT:|P0 |P1 |DOWN:|FAILED:|❌ '
    if printf '%s' "$MESSAGE" | grep -qiE "$ERR_RE"; then
        SUP_LOG="$HOME/.claude/logs/tg-suppressed-alerts.log"
        mkdir -p "$(dirname "$SUP_LOG")"
        printf '%s | chat=%s | %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${TELEGRAM_TEAM_CHAT_ID:--4273200821}" "${MESSAGE//$'\n'/ }" >> "$SUP_LOG"
        echo "🔇 Suppressed (error/infra alert → log, not TG). Bypass: NOTIFY_FORCE=1"
        exit 0
    fi
fi

RESP="$(curl -sS --max-time 15 --retry 2 --retry-delay 2 \
    -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
        \"chat_id\": \"${CHAT_ID}\",
        \"text\": \"${MESSAGE}\",
        \"parse_mode\": \"Markdown\"
    }" 2>&1)"
CURL_RC=$?

if [ $CURL_RC -ne 0 ] || [ -z "$RESP" ]; then
    echo "❌ Network error: curl_rc=$CURL_RC, response_empty=$([ -z "$RESP" ] && echo yes || echo no)" >&2
    echo "   Stderr: ${RESP:-<empty>}" >&2
    exit 2
fi

# Fallback (2026-06-11): legacy Markdown ломается на одиночных подчёркиваниях в URL
# (artvision.pro/_priv-*) — TG отвечает 400 "can't parse entities", legacy-Markdown
# не поддерживает backslash-escape. Повторяем отправку plain-text без parse_mode.
# Прецедент: 5× FAIL доставки превью USmile Антону 10.06.
if printf '%s' "$RESP" | grep -q "can't parse entities"; then
    RESP="$(curl -sS --max-time 15 --retry 2 --retry-delay 2 \
        -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{
            \"chat_id\": \"${CHAT_ID}\",
            \"text\": \"${MESSAGE}\"
        }" 2>&1)"
    if [ $? -ne 0 ] || [ -z "$RESP" ]; then
        echo "❌ Network error on plain-text fallback" >&2
        exit 2
    fi
fi

# Защита от парсинга пустого/HTML-ответа (TG иногда возвращает HTML 502/503)
echo "$RESP" | python3 -c "
import sys, json
raw = sys.stdin.read().strip()
if not raw:
    print('❌ Empty response from Telegram API'); sys.exit(2)
try:
    r = json.loads(raw)
except json.JSONDecodeError:
    print(f'❌ Non-JSON response (likely HTML error page): {raw[:200]}'); sys.exit(2)
if r.get('ok'):
    print('✅ Sent')
else:
    print(f'❌ Error: {r}'); sys.exit(1)
"
