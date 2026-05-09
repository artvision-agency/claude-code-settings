#!/usr/bin/env bash
# tg-bot-deploy-guard.sh — мониторит логи TG-бота после деплоя 5 мин.
#
# Запуск: после `pm2 restart` / `systemctl restart tvorims-bot` или вручную:
#   bash tg-bot-deploy-guard.sh <bot-name> <log-path-on-vps>
#
# Логика:
#   1. SSH на VPS
#   2. Каждые 30 сек 10 раз (5 мин) tail логи
#   3. Считает ошибки: ERROR / Traceback / restart count
#   4. Если >3 рестартов или >5 ERROR → TG-alert + предложение rollback
#
# Cron вариант: */5 * * * * на VPS — постоянный watcher.

set -uo pipefail

BOT="${1:-tvorims-bot}"
LOG_PATH="${2:-~/artvision-tg-bot/vps-bot/logs/bot.log}"
VPS="root@80.90.181.152"

CHECKS=10
INTERVAL=30
ERR_THRESHOLD=5
RESTART_THRESHOLD=3

errors_total=0
restarts_total=0

for i in $(seq 1 $CHECKS); do
  STATS=$(ssh -o ConnectTimeout=10 "$VPS" "tail -200 $LOG_PATH 2>/dev/null | grep -cE 'ERROR|Traceback|Exception|exit code' || echo 0; pm2 jlist 2>/dev/null | jq '.[] | select(.name==\"$BOT\") | .pm2_env.restart_time' 2>/dev/null || echo 0" 2>/dev/null)
  ERR_CNT=$(echo "$STATS" | head -1)
  RESTART_CNT=$(echo "$STATS" | tail -1)
  errors_total=$ERR_CNT
  restarts_total=$RESTART_CNT
  echo "[$i/$CHECKS] errors=$ERR_CNT restarts=$RESTART_CNT"
  if [[ $ERR_CNT -gt $ERR_THRESHOLD || $RESTART_CNT -gt $RESTART_THRESHOLD ]]; then
    break
  fi
  sleep $INTERVAL
done

if [[ $errors_total -gt $ERR_THRESHOLD || $restarts_total -gt $RESTART_THRESHOLD ]]; then
  MSG="🚨 BOT $BOT после деплоя:%0A- ERROR в логах: $errors_total%0A- Рестарты: $restarts_total%0A%0ARекомендация: rollback%0Assh $VPS 'cd ~/artvision-tg-bot && git log --oneline -3 && git revert HEAD'"
  echo "$MSG"
  if [[ -x "$HOME/.claude/scripts/tg-send.sh" ]]; then
    "$HOME/.claude/scripts/tg-send.sh" anton "$MSG" 2>/dev/null || true
  fi
  exit 1
fi

echo "[bot-guard] ✅ $BOT здоров: errors=$errors_total restarts=$restarts_total"
exit 0
