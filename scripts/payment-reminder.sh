#!/bin/bash
set -euo pipefail

# Напоминания об оплате садика и школы
# Запускается ежедневно, проверяет дату и отправляет в TG

BOT_TOKEN=$(python3 -c "import json; t=json.load(open('$HOME/artvision-data/tokens.json')); print(t['telegram']['portal_bot']['token'])")
CHAT_ID="161261562"  # Антон TG

DAY=$(date +%d | sed 's/^0//')
MONTH_NEXT=$(date -v+1m +%B 2>/dev/null || date -d "+1 month" +%B)

send_tg() {
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=$1" \
        -d "parse_mode=MarkdownV2" > /dev/null 2>&1
}

# 23 числа — напоминание про садик
if [ "$DAY" = "23" ]; then
    send_tg "🔔 *Напоминание: оплата САДИКА*

Оплатить до 25 числа на следующий месяц\."
fi

# 1 числа — напоминание про школу
if [ "$DAY" = "1" ]; then
    send_tg "🔔 *Напоминание: оплата ШКОЛЫ*

Оплатить до 3\-4 числа\!
✅ До 3\-4: *6 300 ₽*
❌ После: *7 000 ₽*

Сайт: adainkids\.ru → «Доп\. образование» → «Подготовка к школе» → «Оплатить»"
fi

# 3 числа — последнее напоминание про школу
if [ "$DAY" = "3" ]; then
    send_tg "⚠️ *ПОСЛЕДНИЙ ДЕНЬ: оплата школы по 6 300 ₽\!*

Завтра будет 7 000 ₽\. Оплатить сейчас:
adainkids\.ru → «Доп\. образование» → «Подготовка к школе»"
fi

# 8 числа — предупреждение про Timeweb (за 2 дня до блокировки 10 числа)
if [ "$DAY" = "8" ]; then
    send_tg "🔔 *Напоминание: оплата TIMEWEB*

Аккаунт: \`sr951557\`
Сумма: *1 390 ₽/мес*
Блокировка: *10 числа*

Оплатить завтра, чтобы не отрубили VPS \(artvision\.pro и все клиенты\)\.
Панель: timeweb\.cloud → Биллинг"
fi

# 9 числа — последний день перед блокировкой Timeweb
if [ "$DAY" = "9" ]; then
    send_tg "⚠️ *ПОСЛЕДНИЙ ДЕНЬ: оплата TIMEWEB \(1 390 ₽\)*

Аккаунт: \`sr951557\`
Завтра \(10 числа\) — блокировка VPS\.

На VPS живут: artvision\.pro, тесты клиентов, все боты\.
timeweb\.cloud → Биллинг → Пополнить"
fi
