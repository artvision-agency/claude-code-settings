#!/usr/bin/env bash
# orm-pulse: Оркестратор. Запускает все этапы pipeline для клиента.
# Usage: ./run.sh <client_slug> [mode]
#   mode: full (default) | contractors | reviews | signals | diff | plan | report

set -euo pipefail

CLIENT="${1:?Usage: $0 <client_slug> [mode]}"
MODE="${2:-full}"
SCRIPTS_DIR="$(dirname "$0")"

echo "═══════════════════════════════════════════"
echo "  ORM-PULSE | client: ${CLIENT} | mode: ${MODE}"
echo "  $(date '+%Y-%m-%d %H:%M MSK')"
echo "═══════════════════════════════════════════"

case "$MODE" in
  full)
    echo ""
    echo "🔹 Step 1/5: Sheet snapshot"
    "$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT" || echo "⚠️  Sheet snapshot failed (continuing)"

    echo ""
    echo "🔹 Step 2/5: TG export"
    python3 "$SCRIPTS_DIR/tg-export-clone.py" "$CLIENT" --days 14 || echo "⚠️  TG export failed (continuing)"

    echo ""
    echo "🔹 Step 3/5: Match Sheet ↔ Live (если live dump есть)"
    if [[ -f "/tmp/orm-pulse/${CLIENT}/reviews/in_range.json" ]]; then
      python3 "$SCRIPTS_DIR/match-sheet-live.py" "$CLIENT" || echo "⚠️  Match failed"
    else
      echo "⚠️  No live dump (/tmp/orm-pulse/${CLIENT}/reviews/in_range.json) — пропускаю match"
      mkdir -p "/tmp/orm-pulse/${CLIENT}/match"
      echo "[]" > "/tmp/orm-pulse/${CLIENT}/match/matched.json"
      echo "[]" > "/tmp/orm-pulse/${CLIENT}/match/missing.json"
      echo "[]" > "/tmp/orm-pulse/${CLIENT}/match/organic.json"
    fi

    echo ""
    echo "🔹 Step 4/5: Reconcile (buckets + TG-signals + discrepancies)"
    python3 "$SCRIPTS_DIR/reconcile.py" "$CLIENT" || echo "⚠️  Reconcile failed"

    echo ""
    echo "🔹 Step 5/5: Compose STATUS"
    python3 "$SCRIPTS_DIR/compose-status.py" "$CLIENT"
    ;;

  contractors)
    python3 "$SCRIPTS_DIR/tg-export-clone.py" "$CLIENT" --days 7
    "$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT"
    python3 "$SCRIPTS_DIR/reconcile.py" "$CLIENT"
    python3 -c "
import json
from pathlib import Path
base = Path('/tmp/orm-pulse/${CLIENT}/reconcile')
report = json.loads((base / 'report.json').read_text())
signals = json.loads((base / 'signals.json').read_text())
print('=== ИСПОЛНИТЕЛИ ===')
print(f'Sheet buckets: {report[\"summary\"][\"buckets\"]}')
print(f'Биржа отчиталась: {len(signals[\"bourse_publications\"])} публикаций')
print(f'Биржа просит ещё: {len(signals[\"bourse_pings\"])} пингов')
"
    ;;

  reviews)
    "$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT"
    python3 "$SCRIPTS_DIR/reconcile.py" "$CLIENT"
    ;;

  signals)
    python3 "$SCRIPTS_DIR/tg-export-clone.py" "$CLIENT" --days 3
    python3 "$SCRIPTS_DIR/reconcile.py" "$CLIENT"
    cat "/tmp/orm-pulse/${CLIENT}/reconcile/signals.json" | python3 -m json.tool
    ;;

  diff)
    "$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT"
    cat "$HOME/artvision-data/clients/${CLIENT}/orm/snapshots/latest/_changes.md"
    ;;

  plan)
    python3 "$SCRIPTS_DIR/reconcile.py" "$CLIENT" 2>/dev/null || true
    python3 "$SCRIPTS_DIR/compose-status.py" "$CLIENT" --out /tmp/orm-pulse/${CLIENT}/plan.md
    grep -A 20 "По месяцам" /tmp/orm-pulse/${CLIENT}/plan.md
    ;;

  report)
    "$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT"
    python3 "$SCRIPTS_DIR/tg-export-clone.py" "$CLIENT" --days 14
    python3 "$SCRIPTS_DIR/reconcile.py" "$CLIENT"
    python3 "$SCRIPTS_DIR/compose-status.py" "$CLIENT" --public
    ;;

  orders-state)
    echo "🔹 Step 1/4: Sheet snapshot"
    "$SCRIPTS_DIR/sheet-snapshot.sh" "$CLIENT"
    echo ""
    echo "🔹 Step 2/4: TG export"
    python3 "$SCRIPTS_DIR/tg-export-clone.py" "$CLIENT" --days 14
    echo ""
    echo "🔹 Step 3/4: QComment API snapshot"
    python3 "$SCRIPTS_DIR/qcomment-monitor.py" "$CLIENT" || echo "⚠️  qcomment failed (continuing)"
    echo ""
    echo "🔹 Step 4/4: Orders state — раскладка по корзинам + темп публикаций + не тронутые"
    python3 "$SCRIPTS_DIR/orders-state.py" "$CLIENT"
    ;;

  qcomment)
    echo "🔹 QComment monitor — pull /api/projects + /api/balance + /api/comments"
    python3 "$SCRIPTS_DIR/qcomment-monitor.py" "$CLIENT"
    ;;

  *)
    echo "❌ Unknown mode: $MODE"
    echo "Available: full | contractors | reviews | signals | diff | plan | report | orders-state | qcomment"
    exit 1
    ;;
esac

echo ""
echo "✅ Done."
