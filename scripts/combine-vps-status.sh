#!/usr/bin/env bash
# combine-vps-status.sh — статус задачи, отправленной на VPS-аккаунт
# Использование: combine-vps-status.sh [session-name]   (без аргумента — все combine-* сессии)
set -euo pipefail
VPS_HOST="vps-andrey"
SESSION="${1:-}"

ssh_retry() {
  local n=1
  while (( n <= 3 )); do
    ssh -o ConnectTimeout=20 -o ServerAliveInterval=15 "$VPS_HOST" "$@" && return 0
    sleep 4; n=$((n+1))
  done
  return 1
}

if [[ -z "$SESSION" ]]; then
  echo "=== Активные combine-сессии на VPS ==="
  ssh_retry 'tmux ls 2>/dev/null | grep "^combine-" || echo "нет активных combine-сессий"'
  echo ""
  echo "=== Последние логи ==="
  ssh_retry 'ls -t ~/combine-vps-*.log 2>/dev/null | head -5 || echo "логов нет"'
  exit 0
fi

echo "=== Статус сессии $SESSION ==="
ssh_retry "if tmux has-session -t $SESSION 2>/dev/null; then echo '🟢 РАБОТАЕТ'; else echo '⚪ завершена (или не существует)'; fi"
echo ""
echo "=== Хвост лога ==="
LOG="~/combine-vps-${SESSION#combine-}.log"
ssh_retry "tail -25 $LOG 2>/dev/null || ls -t ~/combine-vps-*.log 2>/dev/null | head -1 | xargs tail -25 2>/dev/null || echo 'лог не найден'"
echo ""
ssh_retry "grep -q COMBINE_VPS_DONE $LOG 2>/dev/null && echo '✅ задача ЗАВЕРШЕНА (COMBINE_VPS_DONE)' || echo '⏳ ещё выполняется'"
