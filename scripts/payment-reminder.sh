#!/bin/bash
set -euo pipefail

# Напоминания об оплате садика и школы
# Запускается ежедневно, проверяет дату и отправляет в TG

BOT_TOKEN=$(python3 -c "import json; t=json.load(open('$HOME/artvision-data/tokens.json')); print(t['telegram']['portal_bot']['token'])")
CHAT_ID="161261562"  # Антон TG

DAY=$(date +%d | sed 's/^0//')
MONTH_NEXT=$(date -v+1m +%B 2>/dev/null || date -d "+1 month" +%B)

send_tg() {
    local text="$1"
    local button_text="${2:-}"
    local button_url="${3:-}"
    local args=(-X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"
        -d "chat_id=${CHAT_ID}"
        --data-urlencode "text=${text}"
        -d "parse_mode=MarkdownV2")
    if [ -n "$button_text" ] && [ -n "$button_url" ]; then
        local rm
        rm=$(printf '{"inline_keyboard":[[{"text":"%s","url":"%s"}]]}' "$button_text" "$button_url")
        args+=(--data-urlencode "reply_markup=${rm}")
    fi
    curl -s "${args[@]}" > /dev/null 2>&1
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

# 8 числа — основное напоминание Timeweb (за 2 дня до блокировки 10 числа)
if [ "$DAY" = "8" ]; then
    send_tg "🔔 *Пополнение TIMEWEB*

Аккаунт: \`sr951557\`
Сумма к оплате: *1 500 ₽*
Расход: *1 390 ₽/мес*
Блокировка VPS: *10 числа*

На VPS живут artvision\.pro, тесты клиентов, все боты\.
СБП в панели Timeweb \(без комиссии\)\." \
        "💳 Перейти к оплате" \
        "https://timeweb.cloud/my/finances/payment"
fi

# 9 числа — дубль если 8-го не оплатили
if [ "$DAY" = "9" ]; then
    send_tg "⚠️ *ПОСЛЕДНИЙ ДЕНЬ: оплата TIMEWEB \(1 500 ₽\)*

Аккаунт: \`sr951557\`
Завтра \(10 числа\) — блокировка VPS\.

Если 8\-го уже оплатил — игнорируй это сообщение\." \
        "💳 Перейти к оплате" \
        "https://timeweb.cloud/my/finances/payment"
fi
