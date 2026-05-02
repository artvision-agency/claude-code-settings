#!/bin/bash
# orm-pulse auto-refresh — pull данные + регенерация command-center + alerts
# Запускается из LaunchAgent каждые 30 мин

set -uo pipefail

CLIENT="${1:?Usage: auto-refresh.sh <client_slug>}"
SCRIPTS_DIR="$(dirname "$(realpath "$0")")"
LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/orm-pulse-${CLIENT}.log"

echo "═══════════════════════════════════════════" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] auto-refresh start: $CLIENT" >> "$LOG"

# 1. QComment snapshot — самое быстрое и критичное
python3 "$SCRIPTS_DIR/qcomment-monitor.py" "$CLIENT" >> "$LOG" 2>&1 || echo "  ⚠️  qcomment failed" >> "$LOG"

# 2. Sheet snapshot (если cookies не истекли)
"$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT" >> "$LOG" 2>&1 || echo "  ⚠️  sheet snapshot failed" >> "$LOG"

# 3. Reviews tracker — отдельный LaunchAgent уже запускает его 4×/день, не дублируем

# 4. Orders state — на основе свежих snapshot'ов
python3 "$SCRIPTS_DIR/orders-state.py" "$CLIENT" >> "$LOG" 2>&1 || echo "  ⚠️  orders-state failed" >> "$LOG"

# 5. Command center HTML deploy
python3 "$SCRIPTS_DIR/command-center.py" "$CLIENT" --deploy >> "$LOG" 2>&1 || echo "  ⚠️  command-center deploy failed" >> "$LOG"

# 6. Alert router (rate-limited internally)
python3 "$SCRIPTS_DIR/alert-router.py" "$CLIENT" >> "$LOG" 2>&1 || echo "  ⚠️  alert-router failed" >> "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] auto-refresh done" >> "$LOG"
