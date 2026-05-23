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

# 5.0 TG contractors monitor (за 30 дней, маркеры pub/rej/req + URL) — ДО attribution
python3 "$SCRIPTS_DIR/tg-contractors-monitor.py" "$CLIENT" --limit 300 >> "$LOG" 2>&1 || echo "  ⚠️  tg-contractors-monitor failed" >> "$LOG"

# 5.0a Screens OCR (фото из чатов исполнителей → Apple Vision OCR → match с sheet)
# ~3-5 мин, поэтому только для blumart и только если есть свежие фото
if [ "$CLIENT" = "blumart" ]; then
    python3 "$SCRIPTS_DIR/screens-pull-ocr.py" >> "$LOG" 2>&1 || echo "  ⚠️  screens-pull-ocr failed" >> "$LOG"
fi

# 5.1 Attribution report (текст × источник × дата заказа × дата публикации × live статус + TG)
python3 "$SCRIPTS_DIR/attribution-report.py" "$CLIENT" >> "$LOG" 2>&1 || echo "  ⚠️  attribution-report failed" >> "$LOG"

# 5.2 qcomment auto-accept-pending (live-guard сам блокирует если нет match в live)
# Прецедент self-corrections.md #14 — guard защищает от accept «На проверке».
if [ "$CLIENT" = "blumart" ]; then
    python3 "$SCRIPTS_DIR/qcomment-accept-pending.py" accept --all >> "$LOG" 2>&1 || echo "  ⚠️  qcomment accept (или live-guard blocked)" >> "$LOG"
fi

# 6. Alert router (rate-limited internally)
python3 "$SCRIPTS_DIR/alert-router.py" "$CLIENT" >> "$LOG" 2>&1 || echo "  ⚠️  alert-router failed" >> "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] auto-refresh done" >> "$LOG"
