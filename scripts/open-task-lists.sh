#!/bin/sh
# open-task-lists.sh — открыть списки задач (ops.html + Asana) при включении компа / выходе из сна.
# Запрос Антона 11.06.2026. Вызывается: LaunchAgent pro.artvision.tasklists-open (логин) + ~/.wakeup (пробуждение).
# Троттлинг: не чаще раза в TASKLISTS_THROTTLE_MIN минут. Отключить: touch ~/.claude/.tasklists-open-off
# Codex-review fixes 11.06: atomic lock (mkdir), stamp пишется ПОСЛЕ успешных open.

LOG="$HOME/Library/Logs/artvision-tasklists-open.log"
STAMP="$HOME/.claude/.tasklists-open-last"
LOCK="$HOME/.claude/.tasklists-open.lock"
THROTTLE_MIN="${TASKLISTS_THROTTLE_MIN:-30}"

[ -f "$HOME/.claude/.tasklists-open-off" ] && exit 0

# атомарный lock против гонки LaunchAgent vs wakeup
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "$(date '+%F %T') skip (lock held)" >> "$LOG"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

now=$(date +%s)
if [ -f "$STAMP" ]; then
  last=$(cat "$STAMP" 2>/dev/null || echo 0)
  diff=$(( (now - last) / 60 ))
  if [ "$diff" -lt "$THROTTLE_MIN" ]; then
    echo "$(date '+%F %T') skip (throttle ${diff}m < ${THROTTLE_MIN}m)" >> "$LOG"
    exit 0
  fi
fi

{
  echo "$(date '+%F %T') opening task lists"
  ok=1
  /usr/bin/open "https://artvision.pro/ops.html" || ok=0
  sleep 1
  /usr/bin/open "https://app.asana.com/" || ok=0
  # stamp только при успехе обоих open — иначе повтор не блокируется
  [ "$ok" = "1" ] && echo "$now" > "$STAMP" || echo "$(date '+%F %T') open failed, stamp not written"
} >> "$LOG" 2>&1
