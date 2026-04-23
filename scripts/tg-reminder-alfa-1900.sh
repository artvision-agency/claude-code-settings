#!/bin/bash
# Одноразовое напоминание по кредиту Альфа — 23.04.2026 19:00 MSK
# Вызывается из LaunchAgent com.artvision.reminder-alfa-1900
# После отправки — автоматически самоудаляется

set -uo pipefail

LOG=/tmp/reminder-alfa-1900.log
echo "[$(date)] Starting reminder..." >> "$LOG"

# Токен из tokens.json или .env
TG_TOKEN=$(jq -r '.telegram.bot_token // .telegram_bot_token // ""' /Users/antonk/artvision-data/tokens.json 2>/dev/null)
if [ -z "$TG_TOKEN" ] || [ "$TG_TOKEN" = "null" ]; then
    TG_TOKEN=$(grep -hE "^TELEGRAM_BOT_TOKEN=|^BOT_TOKEN=" \
        /Users/antonk/artvision-tg-bot/.env.local \
        /Users/antonk/artvision-tg-bot/.env 2>/dev/null | \
        head -1 | cut -d= -f2 | tr -d '"' | tr -d "'")
fi

if [ -z "$TG_TOKEN" ]; then
    echo "[$(date)] ERROR: TG_TOKEN not found" >> "$LOG"
    exit 1
fi

# Сообщение в файл (кириллица)
MSG_FILE=/tmp/reminder-alfa-msg.txt
cat > "$MSG_FILE" <<'EOF'
🚨 КРЕДИТ АЛЬФА — 3 действия ДО 24.04

Завтра 24.04 списание 159 101,61 ₽ с ···5994.

1️⃣ ПОПОЛНИТЬ СЧЁТ ···5994 на 159 101,61 ₽
    Без этого: просрочка → испорченная КИ → рефинанс невозможен.

2️⃣ ЗАКАЗАТЬ ЕГРН на Каменноостровский 1-3 кв.39
    Госуслуги → Выписка ЕГРН → ~350 ₽ → 3 дня

3️⃣ ПОЗВОНИТЬ В АЛЬФУ: 8-800-200-00-00
    Договор F0PM1020S24010900331
    Вопросы: условия снятия залога? Рефинанс внутри? Страховка — сумма/год?

Полный план: ~/artvision-data/personal/alfa-zalog/HANDOVER-2026-04-23.md
Залог на квартире подтверждён (100%). 77% платежей за 2 года = проценты.
Рефинанс в Сбер/ВТБ — приоритет #1 (но только после звонка в Альфу).
EOF

# Отправка
RESP=$(curl -s --max-time 20 -X POST \
    "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=161261562" \
    --data-urlencode "text=$(cat $MSG_FILE)")

echo "[$(date)] TG response: $RESP" >> "$LOG"
rm -f "$MSG_FILE"

# Самоудаление LaunchAgent после успешной отправки
if echo "$RESP" | grep -q '"ok":true'; then
    echo "[$(date)] SUCCESS — unloading LaunchAgent" >> "$LOG"
    launchctl unload /Users/antonk/Library/LaunchAgents/com.artvision.reminder-alfa-1900.plist 2>/dev/null
    rm -f /Users/antonk/Library/LaunchAgents/com.artvision.reminder-alfa-1900.plist
    # скрипт оставляем для лога
fi
