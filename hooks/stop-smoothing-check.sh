#!/bin/bash
# Stop hook: запускает LLM-анализ сессии на сглаживание углов
# Работает в фоне (async), не блокирует завершение сессии
# Результат → ~/.claude/smoothing-reports/

set -euo pipefail

SCRIPT="/Users/antonk/.claude/scripts/smoothing-detector.py"

if [ ! -f "$SCRIPT" ]; then
  echo "[smoothing] Script not found: $SCRIPT"
  exit 0
fi

# Запускаем анализ (--analyze вызывает claude -p)
python3 "$SCRIPT" --analyze 2>&1 || true

exit 0
