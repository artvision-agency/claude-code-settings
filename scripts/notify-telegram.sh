#!/bin/bash
# Отправка уведомлений в Telegram чат команды
# Использование: notify-telegram.sh "Текст сообщения"

BOT_TOKEN="8399522625:AAGeVvP1WeyijXTcRByiynPOXncBFUwLKQ4"
CHAT_ID="${TELEGRAM_TEAM_CHAT_ID:--4273200821}"  # Artvision team chat

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "Usage: notify-telegram.sh \"Message text\""
    exit 1
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
