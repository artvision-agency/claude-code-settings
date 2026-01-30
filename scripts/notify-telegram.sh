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

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
        \"chat_id\": \"${CHAT_ID}\",
        \"text\": \"${MESSAGE}\",
        \"parse_mode\": \"Markdown\"
    }" | python3 -c "import sys,json; r=json.load(sys.stdin); print('✅ Sent' if r.get('ok') else f'❌ Error: {r}')"
