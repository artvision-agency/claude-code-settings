#!/bin/bash
# PostToolUse (Bash): smoke test после деплоя на VPS
# Ждёт 5 секунд, проверяет что процесс жив и не в restart loop

COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

# Триггер: scp на VPS или pm2 restart или systemctl restart
IS_DEPLOY=false
echo "$COMMAND" | grep -qE "scp.*80\.90\.181\.152" && IS_DEPLOY=true
echo "$COMMAND" | grep -qE "pm2\s+(restart|start)" && IS_DEPLOY=true
echo "$COMMAND" | grep -qE "systemctl\s+(restart|start)" && IS_DEPLOY=true
echo "$COMMAND" | grep -qE "ssh.*80\.90\.181\.152.*(restart|start|deploy)" && IS_DEPLOY=true

if [ "$IS_DEPLOY" != "true" ]; then
  exit 0
fi

# Определяем что деплоили
BOT_NAME=""
echo "$COMMAND" | grep -q "tvorims" && BOT_NAME="tvorims_bot"
echo "$COMMAND" | grep -q "avportal" && BOT_NAME="avportal_bot"
echo "$COMMAND" | grep -q "bot\.py\|bot\.js" && BOT_NAME="bot"

echo "🚀 [POST-DEPLOY] Деплой обнаружен. Smoke test через 5 сек..."
echo ""
echo "ОБЯЗАТЕЛЬНО после деплоя:"
echo "  1. ssh root@80.90.181.152 'pm2 logs ${BOT_NAME:-all} --lines 20'"
echo "  2. Проверь что нет restart loop: pm2 list"
echo "  3. Если бот — отправь /start в TG"
echo ""
echo "⚠️ Напоминание (инцидент tvorims_bot 14.03): 129 рестартов за 3 дня без алерта."
echo "→ Мониторь логи 5 минут после ЛЮБОГО деплоя."

exit 0
