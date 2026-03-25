#!/bin/bash
# SessionStart hook: показывает непрочитанные smoothing-отчёты
set -euo pipefail

REPORTS_DIR="$HOME/.claude/smoothing-reports"
SEEN_FILE="$REPORTS_DIR/.last_seen"

if [ ! -d "$REPORTS_DIR" ]; then
  exit 0
fi

# Находим отчёты новее чем last_seen
NEW_REPORTS=()
if [ -f "$SEEN_FILE" ]; then
  while IFS= read -r report; do
    NEW_REPORTS+=("$report")
  done < <(find "$REPORTS_DIR" -name "*.md" -newer "$SEEN_FILE" -type f 2>/dev/null | sort -r)
else
  while IFS= read -r report; do
    NEW_REPORTS+=("$report")
  done < <(find "$REPORTS_DIR" -name "*.md" -type f 2>/dev/null | sort -r | head -3)
fi

if [ ${#NEW_REPORTS[@]} -eq 0 ]; then
  exit 0
fi

# Проверяем есть ли SMOOTHING_DETECTED
SMOOTHING_COUNT=0
for report in "${NEW_REPORTS[@]}"; do
  if grep -q "SMOOTHING_DETECTED" "$report" 2>/dev/null; then
    SMOOTHING_COUNT=$((SMOOTHING_COUNT + 1))
  fi
done

if [ "$SMOOTHING_COUNT" -gt 0 ]; then
  echo ""
  echo "🔴 SMOOTHING ALERT: $SMOOTHING_COUNT отчётов с обнаруженным сглаживанием"
  echo "   Отчёты: $REPORTS_DIR/"
  for report in "${NEW_REPORTS[@]}"; do
    if grep -q "SMOOTHING_DETECTED" "$report" 2>/dev/null; then
      BASENAME=$(basename "$report")
      CRITICAL=$(grep -c "CRITICAL" "$report" 2>/dev/null || true)
      HIGH=$(grep -c "Уровень: HIGH" "$report" 2>/dev/null || true)
      echo "   - $BASENAME (CRITICAL:$CRITICAL HIGH:$HIGH)"
    fi
  done
  echo "   ПРОЧИТАЙ отчёты и исправь поведение."
  echo ""
fi

# Обновляем last_seen
touch "$SEEN_FILE"

exit 0
