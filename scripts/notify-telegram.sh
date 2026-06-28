#!/bin/bash
# Отправка уведомлений в Telegram чат команды
# Использование: notify-telegram.sh "Текст сообщения"
#
# ── BOT FALLBACK CHAIN (2026-06-28): portal_bot протух (getMe → 401 Unauthorized),
#    из-за чего падали все уведомления (напр. BluMart ORM). Теперь скрипт перебирает
#    цепочку ботов: при 401/Unauthorized от текущего бота автоматически переходит к
#    следующему ЖИВОМУ боту. Токены читаются из tokens.json в РАНТАЙМЕ (НЕ хардкод —
#    файл синкается в публичный репо, self-corrections #31).
#    Порядок по умолчанию: portal_bot → vps_bot → backup_bot.
#    Переопределить: TG_BOT_CHAIN="vps_bot portal_bot" notify-telegram.sh "..."
#    Настоящий фикс = новый токен portal_bot через BotFather (это человек).

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

# Читает токен бота из tokens.json по имени (telegram.<bot>.token или telegram.<bot> строкой).
_bot_token() {
    python3 -c "import json,os,sys
d=json.load(open(os.path.expanduser('~/artvision-data/tokens.json')))['telegram'].get('$1')
print(d if isinstance(d,str) else (d.get('token','') if isinstance(d,dict) else '')) if d else print('')" 2>/dev/null
}

# Отправка одним ботом. Аргумент: BOT_TOKEN. Печатает сырой ответ TG в stdout.
# Внутри — Markdown-попытка + plain-text fallback на "can't parse entities".
_send_once() {
    local BOT_TOKEN="$1" RESP CURL_RC
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
        echo "__NETERR__ curl_rc=$CURL_RC response_empty=$([ -z "$RESP" ] && echo yes || echo no) stderr=${RESP:-<empty>}"
        return 2
    fi

    # Fallback (2026-06-11): legacy Markdown ломается на одиночных подчёркиваниях в URL
    # (artvision.pro/_priv-*) — TG отвечает 400 "can't parse entities". Повторяем plain-text.
    if printf '%s' "$RESP" | grep -q "can't parse entities"; then
        RESP="$(curl -sS --max-time 15 --retry 2 --retry-delay 2 \
            -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -H "Content-Type: application/json" \
            -d "{
                \"chat_id\": \"${CHAT_ID}\",
                \"text\": \"${MESSAGE}\"
            }" 2>&1)"
        if [ $? -ne 0 ] || [ -z "$RESP" ]; then
            echo "__NETERR__ plain-text fallback failed"
            return 2
        fi
    fi
    printf '%s' "$RESP"
    return 0
}

BOT_CHAIN="${TG_BOT_CHAIN:-portal_bot vps_bot backup_bot}"
RESP=""
USED_BOT=""
NETERR=0

for BOT in $BOT_CHAIN; do
    BOT_TOKEN="$(_bot_token "$BOT")"
    [ -z "$BOT_TOKEN" ] && continue   # нет токена в tokens.json → следующий бот
    RESP="$(_send_once "$BOT_TOKEN")"
    if printf '%s' "$RESP" | grep -q '^__NETERR__'; then
        # транзиентная сеть — НЕ переключаем бота (сеть общая), сообщаем и выходим
        NETERR=1
        echo "❌ Network error via $BOT: ${RESP#__NETERR__ }" >&2
        break
    fi
    # Проверяем ответ TG. 401/Unauthorized → бот мёртв → следующий бот в цепочке.
    if printf '%s' "$RESP" | grep -qE '"error_code":401|Unauthorized'; then
        echo "⚠️  $BOT dead (401 Unauthorized) → trying next bot" >&2
        RESP=""
        continue
    fi
    USED_BOT="$BOT"
    break
done

if [ "$NETERR" = "1" ]; then
    exit 2
fi

if [ -z "$RESP" ]; then
    echo "❌ All bots in chain failed (no live bot / all 401). Chain: $BOT_CHAIN" >&2
    exit 2
fi

# Защита от парсинга пустого/HTML-ответа (TG иногда возвращает HTML 502/503)
export TG_USED_BOT="$USED_BOT"
echo "$RESP" | python3 -c "
import sys, json, os
raw = sys.stdin.read().strip()
bot = os.environ.get('TG_USED_BOT','')
if not raw:
    print('❌ Empty response from Telegram API'); sys.exit(2)
try:
    r = json.loads(raw)
except json.JSONDecodeError:
    print(f'❌ Non-JSON response (likely HTML error page): {raw[:200]}'); sys.exit(2)
if r.get('ok'):
    mid = r.get('result',{}).get('message_id')
    print(f'✅ Sent via {bot} (message_id={mid})')
else:
    print(f'❌ Error: {r}'); sys.exit(1)
"
