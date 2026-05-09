#!/usr/bin/env bash
# stop-skill-audit.sh — Stop hook
#
# Запускает audit-session-tools.py и дописывает в recap секцию «Пропущенные скиллы»
# если есть skipped relevant.

set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

AUDIT_SCRIPT="$HOME/.claude/scripts/audit-session-tools.py"
RECAP="$HOME/artvision-data/sync/recaps/${SESSION_ID}.md"

[[ ! -x "$AUDIT_SCRIPT" ]] && exit 0
[[ ! -f "$RECAP" ]] && exit 0

# Skip если уже добавляли
grep -q "## 🔍 Пропущенные скиллы" "$RECAP" && exit 0

OUTPUT=$(python3 "$AUDIT_SCRIPT" "$SESSION_ID" 2>&1)
[[ -z "$OUTPUT" ]] && exit 0

# Извлечь секцию «НЕ ИСПОЛЬЗОВАНО» (первые 12 пунктов)
SKIPPED=$(echo "$OUTPUT" | awk '/^❌ НЕ ИСПОЛЬЗОВАНО/,/^📊/' | grep -E '^\s*•' | head -12)

[[ -z "$SKIPPED" ]] && exit 0

cat >> "$RECAP" <<EOF

---

## 🔍 Пропущенные скиллы (auto-audit at stop)

$(echo "$OUTPUT" | grep -E '^📊' | head -3)

Топ доступных но не вызванных:
${SKIPPED}

📝 Полный отчёт: \`python3 ~/.claude/scripts/audit-session-tools.py ${SESSION_ID}\`
EOF

exit 0
