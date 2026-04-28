#!/usr/bin/env bash
# Stop hook: показывает явный статус recap текущей сессии.
# Решает проблему: встроенный «※ recap» Claude Code не говорит явно
# «решена задача или нет» — этот хук выводит ✅/⚠️/❌ + N/M acceptance.
#
# Bypass: RECAP_STATUS_SKIP=1
set -u

[[ "${RECAP_STATUS_SKIP:-0}" == "1" ]] && exit 0

# Читаем JSON от harness через stdin (как и другие Stop-хуки)
INPUT="$(cat 2>/dev/null || true)"
SESSION_ID="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("session_id",""))
except: pass' 2>/dev/null)"

# Fallback: env или последний recap-файл
SESSION_ID="${SESSION_ID:-${CLAUDE_SESSION_ID:-}}"
RECAPS_DIR="$HOME/artvision-data/sync/recaps"
[[ -z "$SESSION_ID" && -d "$RECAPS_DIR" ]] && \
  SESSION_ID="$(ls -t "$RECAPS_DIR"/*.md 2>/dev/null | head -1 | xargs -n1 basename 2>/dev/null | sed 's/\.md$//')"

RECAP="$RECAPS_DIR/${SESSION_ID}.md"
[[ ! -f "$RECAP" ]] && exit 0

# Считаем acceptance criteria только в секции "## Acceptance criteria"
ACCEPT_BLOCK="$(awk '
  /^## Acceptance criteria/ {flag=1; next}
  /^## / && flag {exit}
  flag {print}
' "$RECAP")"

DONE="$(printf '%s\n' "$ACCEPT_BLOCK" | grep -cE '^- \[x\]' || true)"
OPEN="$(printf '%s\n' "$ACCEPT_BLOCK" | grep -cE '^- \[ \]' || true)"
TOTAL=$((DONE + OPEN))

# Финальный статус (если есть в файле)
FINAL_RAW="$(awk '
  /^## Финальный статус/ {flag=1; next}
  /^## / && flag {exit}
  flag {print}
' "$RECAP" | grep -m1 -oE '✅ COMPLETED|⚠️ PARTIAL|❌ ABANDONED' || true)"

# Решаем иконку: финальный статус — приоритет, иначе по счёту
if [[ "$FINAL_RAW" == "✅ COMPLETED" ]] || { [[ "$TOTAL" -gt 0 ]] && [[ "$OPEN" -eq 0 ]]; }; then
  ICON="✅ РЕШЁН ПОЛНОСТЬЮ"
elif [[ "$FINAL_RAW" == "❌ ABANDONED" ]] || { [[ "$TOTAL" -gt 0 ]] && [[ "$DONE" -eq 0 ]]; }; then
  ICON="❌ НЕ РЕШЁН"
elif [[ "$FINAL_RAW" == "⚠️ PARTIAL" ]] || [[ "$OPEN" -gt 0 ]]; then
  ICON="⚠️ ЧАСТИЧНО"
else
  # acceptance пуст и финального статуса нет — recap не заполнен, молчим
  exit 0
fi

# Вывод (на stdout — попадёт в session output)
printf '\n🎯 Recap (sessionId: %s): %s — %d/%d acceptance закрыты\n' \
  "$SESSION_ID" "$ICON" "$DONE" "$TOTAL"

exit 0
