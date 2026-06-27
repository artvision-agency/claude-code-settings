#!/usr/bin/env bash
# ppc-report-usmile-runner.sh — еженедельный (пн) + 1-го числа черновик PPC-отчёта USmile.
# Запускается launchd (pro.artvision.ppc-report-usmile). ЗАПИСЬ черновика (без --show-cost:
# расход 🔒 за паролем — это запись в файл, не показ Антону на экране).
set -uo pipefail
export PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/usr/bin:/bin"
PY=python3
DATA="$HOME/artvision-data"
RPT="$DATA/scripts/ppc/ppc-report.py"
OUTDIR="$DATA/clients/usmile/ppc/reports"
mkdir -p "$OUTDIR"

TODAY=$(date +%Y-%m-%d)
MONTH_START=$(date +%Y-%m-01)
OUT="$OUTDIR/draft-$TODAY.md"

"$PY" "$RPT" --login yail307 --from "$MONTH_START" --to "$TODAY" --out "$OUT"
RC=$?

if [[ $RC -eq 0 && -f "$OUT" ]]; then
  "$HOME/.claude/scripts/tg-send.sh" anton "📊 USmile: черновик PPC-отчёта готов ($MONTH_START → $TODAY) → clients/usmile/ppc/reports/draft-$TODAY.md (расход 🔒 в файле)" || true
else
  "$HOME/.claude/scripts/tg-send.sh" anton "⚠️ USmile PPC-отчёт: сборка черновика упала (rc=$RC, $TODAY). Проверь ppc-report.py/токен yail307." || true
fi
exit 0
