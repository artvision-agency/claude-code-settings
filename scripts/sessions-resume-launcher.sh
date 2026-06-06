#!/usr/bin/env bash
# sessions-resume-launcher.sh — резюмит N последних активных Claude-сессий в окнах Ghostty.
# БЕЗ tmux. Механизм: open -na Ghostty.app --args -e /bin/zsh -lc '...' (как claude-asana.sh).
# --resume загружает контекст и ЖДЁТ ввода (не churns) → окна открываются «где остановился».
# Combine-окно (asana+очередь) активно работает (даётся /combine) — только в LOGIN-режиме.
#
# Использование:
#   sessions-resume-launcher.sh [N]            # LOGIN: combine + N resume (по умолч. N=6)
#   sessions-resume-launcher.sh [N] --wake     # WAKE: только resume УПАВШИХ (без combine)
# Статус: подключён в bootstrap-mac-login.sh + ~/.wakeup.

set -euo pipefail
N=6; WAKE=0
for a in "$@"; do
  case "$a" in
    --wake) WAKE=1 ;;
    [0-9]*) N="$a" ;;
  esac
done

LOG="$HOME/Library/Logs/artvision-sessions-resume.log"
exec >> "$LOG" 2>&1
echo "=== sessions-resume $(date '+%F %T') N=$N WAKE=$WAKE ==="

CLAUDE_BIN="$HOME/.local/bin/claude"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="claude"
PROJ_ROOT="$HOME/.claude/projects"
declare -A DIRMAP=(
  ["-Users-antonk-artvision-data"]="$HOME/artvision-data"
  ["-Users-antonk-artvision-tg-bot"]="$HOME/artvision-tg-bot"
  ["-Users-antonk-devops-agent"]="$HOME/devops-agent"
)

open_win() {  # $1=cwd  $2=claude-args(строка)
  local cwd="$1" cargs="$2"
  /usr/bin/open -na "Ghostty.app" --args -e /bin/zsh -lc \
    "cd '$cwd' && exec '$CLAUDE_BIN' --dangerously-skip-permissions $cargs"
  sleep 1.2
}

# --- LOGIN: окно combine (asana + прогон очереди). На WAKE пропускаем (без спама). ---
if [ "$WAKE" -eq 0 ]; then
  echo "launch combine window (ops)"
  open_win "$HOME/artvision-data" "'/combine'"
fi

# --- N последних сессий (>=10 строк = была реальная работа), дедуп по pgrep ---
mapfile -t FILES < <(
  for enc in "${!DIRMAP[@]}"; do
    d="$PROJ_ROOT/$enc"; [ -d "$d" ] || continue
    for f in "$d"/*.jsonl; do
      [ -e "$f" ] || continue
      l=$(wc -l < "$f" 2>/dev/null || echo 0); [ "$l" -ge 10 ] || continue
      echo "$(stat -f '%m' "$f")|$enc|$f"
    done
  done | sort -rn | head -n "$N"
)

count=0
for row in "${FILES[@]}"; do
  [ -n "$row" ] || continue
  enc="${row#*|}"; enc="${enc%%|*}"
  f="${row##*|}"; sid="$(basename "$f" .jsonl)"
  cwd="${DIRMAP[$enc]:-$HOME/artvision-data}"
  if pgrep -f -- "--resume $sid" >/dev/null 2>&1; then
    echo "skip (running): ${sid:0:8}"; continue
  fi
  echo "resume: ${sid:0:8} cwd=$cwd"
  open_win "$cwd" "--resume '$sid'"
  count=$((count+1))
done
echo "done: $( [ "$WAKE" -eq 0 ] && echo 'combine +' ) $count resumed (WAKE=$WAKE)"
