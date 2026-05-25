#!/usr/bin/env bash
# combine-vps-dispatch.sh — отправить автономную задачу на VPS-аккаунт (adw.artvision.pro, юзер andrey)
# Запускается с локального Mac (аккаунт justtrance). Параллелит независимые задачи на второй аккаунт.
#
# Использование:
#   combine-vps-dispatch.sh "<prompt>"          — отправить произвольный prompt
#   combine-vps-dispatch.sh --combine "<filter>" — запустить /combine с фильтром на VPS
#
# Возвращает: tmux-сессию + путь к логу. Возврат мгновенный (задача крутится в фоне на VPS).
# Координация результатов — через git (VPS коммитит+пушит, локально git pull).
#
# Прецедент: session a09dc922 (2026-05-25). См. ~/.claude/rules/vps-parallel-combine.md
set -euo pipefail

VPS_HOST="vps-andrey"        # ssh-хост: User andrey (non-root → auto-mode работает)
REPO="~/artvision-data"
TS="$(date +%Y%m%d_%H%M%S)"
SESSION="combine-${TS}"
LOG="~/combine-vps-${TS}.log"

MODE="prompt"
if [[ "${1:-}" == "--combine" ]]; then MODE="combine"; shift; fi
PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then
  echo "ОШИБКА: пустой prompt. Использование: $0 [--combine] \"<задача>\"" >&2
  exit 1
fi

# Для режима --combine оборачиваем в вызов комбайна с фильтром
if [[ "$MODE" == "combine" ]]; then
  FULL_PROMPT="Запусти /combine для задач по фильтру: ${PROMPT}. Работай автономно, коммить и пуш результаты в git по завершении каждой задачи. Не трогай файлы вне указанного фильтра."
else
  FULL_PROMPT="$PROMPT"
fi

# ssh-обёртка с ретраями (соединение к VPS иногда рвётся)
ssh_retry() {
  local tries=3 n=1
  while (( n <= tries )); do
    if ssh -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "$VPS_HOST" "$@"; then
      return 0
    fi
    echo "[dispatch] ssh попытка $n/$tries не удалась, повтор..." >&2
    sleep 5; n=$((n+1))
  done
  return 1
}

echo "[dispatch] → VPS ($VPS_HOST), сессия tmux: $SESSION"

# 1. git pull (синхронизация перед стартом) + 2. запуск headless combine в detached tmux
# Экранируем prompt для безопасной передачи
ESCAPED_PROMPT=$(printf '%q' "$FULL_PROMPT")

ssh_retry "cd $REPO && \
  git -c core.symlinks=false pull --no-edit origin feat/ops-crm-v1 2>&1 | tail -2; \
  tmux kill-session -t $SESSION 2>/dev/null; \
  tmux new-session -d -s $SESSION \"cd $REPO && claude -p $ESCAPED_PROMPT --dangerously-skip-permissions --permission-mode bypassPermissions > $LOG 2>&1; echo COMBINE_VPS_DONE >> $LOG\" && \
  echo '[dispatch] tmux-сессия запущена'"

echo ""
echo "✅ Задача отправлена на VPS-аккаунт (adw.artvision.pro)"
echo "   tmux-сессия: $SESSION"
echo "   лог:         $LOG (на VPS)"
echo ""
echo "Проверить статус:  ~/.claude/scripts/combine-vps-status.sh $SESSION"
echo "Забрать результат: ~/.claude/scripts/combine-vps-collect.sh"
