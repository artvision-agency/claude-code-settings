#!/bin/bash
set -euo pipefail

# TG Bot Pre-flight Check
# Запускать ПЕРЕД деплоем любого TG-бота
# Usage: tg-bot-preflight.sh <bot_token> <vps_host> [process_name]

BOT_TOKEN="${1:-}"
VPS_HOST="${2:-80.90.181.152}"
PROC_NAME="${3:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
    local status="$1" msg="$2"
    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}[OK]${NC} $msg"
        PASS=$((PASS+1))
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}[WARN]${NC} $msg"
        WARN=$((WARN+1))
    else
        echo -e "${RED}[FAIL]${NC} $msg"
        FAIL=$((FAIL+1))
    fi
}

echo "=== TG Bot Pre-flight Check ==="
echo ""

# 1. Token validation
if [ -z "$BOT_TOKEN" ]; then
    check "fail" "BOT_TOKEN не указан (аргумент 1)"
else
    RESULT=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe" 2>/dev/null)
    if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']" 2>/dev/null; then
        BOT_USERNAME=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])")
        check "ok" "Токен валиден: @${BOT_USERNAME}"
    else
        check "fail" "Токен невалиден!"
    fi

    # 2. Check for conflict (другой инстанс уже polling)
    WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" 2>/dev/null)
    PENDING=$(echo "$WEBHOOK_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'].get('pending_update_count', 0))" 2>/dev/null || echo "0")
    WEBHOOK_URL=$(echo "$WEBHOOK_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'].get('url', ''))" 2>/dev/null || echo "")

    if [ -n "$WEBHOOK_URL" ]; then
        check "warn" "Webhook установлен: $WEBHOOK_URL (удали если используешь polling)"
    else
        check "ok" "Webhook не установлен (polling mode)"
    fi

    # 3. Group privacy
    CAN_READ=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'].get('can_read_all_group_messages', False))" 2>/dev/null || echo "False")
    if [ "$CAN_READ" = "True" ]; then
        check "ok" "Group Privacy OFF — бот видит все сообщения в группах"
    else
        check "warn" "Group Privacy ON — бот НЕ видит сообщения в группах! Отключи в @BotFather → Bot Settings → Group Privacy → Turn off"
    fi
fi

# 4. Локальные процессы с тем же ботом
LOCAL_PROCS=$(pgrep -f "bot.*\.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$LOCAL_PROCS" -gt 0 ]; then
    check "warn" "Найдено $LOCAL_PROCS локальных процессов бота — УБЕЙ перед деплоем на VPS!"
    pgrep -af "bot.*\.py" 2>/dev/null || true
else
    check "ok" "Локальных процессов бота нет"
fi

# 5. VPS проверки
if ssh -o ConnectTimeout=5 "root@${VPS_HOST}" "echo ok" 2>/dev/null | grep -q ok; then
    check "ok" "VPS $VPS_HOST доступен"

    # Проверить дубли на VPS
    if [ -n "$PROC_NAME" ]; then
        VPS_COUNT=$(ssh "root@${VPS_HOST}" "pm2 jlist 2>/dev/null | python3 -c \"import sys,json; print(sum(1 for p in json.load(sys.stdin) if p['name']=='${PROC_NAME}' and p['pm2_env']['status']=='online'))\"" 2>/dev/null || echo "0")
        if [ "$VPS_COUNT" -gt 1 ]; then
            check "fail" "На VPS запущено $VPS_COUNT инстансов '$PROC_NAME' — конфликт!"
        elif [ "$VPS_COUNT" -eq 1 ]; then
            check "warn" "Процесс '$PROC_NAME' уже запущен — будет рестартнут"
        else
            check "ok" "Процесс '$PROC_NAME' не запущен — чистый старт"
        fi
    fi

    # ffmpeg
    if ssh "root@${VPS_HOST}" "which ffmpeg" >/dev/null 2>&1; then
        check "ok" "ffmpeg установлен на VPS"
    else
        check "fail" "ffmpeg НЕ установлен на VPS (apt install ffmpeg)"
    fi

    # RAM
    FREE_MB=$(ssh "root@${VPS_HOST}" "free -m | awk '/Mem:/ {print \$7}'" 2>/dev/null || echo "0")
    if [ "$FREE_MB" -gt 500 ]; then
        check "ok" "Свободно ${FREE_MB}MB RAM"
    else
        check "warn" "Мало RAM: ${FREE_MB}MB свободно"
    fi
else
    check "fail" "VPS $VPS_HOST недоступен"
fi

# 6. .env файл
if [ -f ".env" ]; then
    if grep -q "BOT_TOKEN" .env; then
        check "ok" ".env содержит BOT_TOKEN"
    else
        check "fail" ".env не содержит BOT_TOKEN"
    fi
else
    check "warn" ".env файл не найден в текущей директории"
fi

echo ""
echo "=== Итого: ${GREEN}${PASS} OK${NC}, ${YELLOW}${WARN} WARN${NC}, ${RED}${FAIL} FAIL${NC} ==="

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}ДЕПЛОЙ ЗАБЛОКИРОВАН — исправь FAIL ошибки${NC}"
    exit 1
fi
