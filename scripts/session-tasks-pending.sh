#!/usr/bin/env bash
# session-tasks-pending.sh — выводит pending задачи из TODO.md текущего cwd
# Используется в SessionStart hook: Claude видит → создаёт TaskCreate
set -euo pipefail

CWD="${PWD:-$(pwd)}"
case "$CWD" in
  */artvision-tg-bot*) TODO="$HOME/artvision-tg-bot/TODO.md" ;;
  */devops-agent*)     TODO="$HOME/devops-agent/TODO.md" ;;
  */artvision-data/presale*)  TODO="$HOME/artvision-data/presale/TODO.md" ;;
  */artvision-data/products*) TODO="$HOME/artvision-data/products/TODO.md" ;;
  *)                   TODO="$HOME/artvision-data/TODO.md" ;;
esac

[ -f "$TODO" ] || { echo "[session-tasks] TODO не найден: $TODO"; exit 0; }

PENDING=$(grep -c '^- \[ \]' "$TODO" 2>/dev/null || echo 0)
PENDING=${PENDING:-0}
[ "$PENDING" -eq 0 ] && { echo "[session-tasks] $TODO — pending: 0"; exit 0; }

echo "═══ PENDING TASKS ($PENDING) — $TODO ═══"
grep '^- \[ \]' "$TODO" | head -10 | sed 's/^- \[ \] /  · /'
[ "$PENDING" -gt 10 ] && echo "  … +$((PENDING-10)) ещё"
echo "═══ → создай TaskCreate для high-priority ═══"
