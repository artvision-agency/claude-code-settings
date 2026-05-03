#!/usr/bin/env bash
# stop-recap-completeness.sh — Stop hook
#
# Проверяет recap.md имеет минимальный набор полей:
#   - Цель сессии (не пусто)
#   - Минимум 1 deliverable (- [x] или - [ ])
#   - Минимум 1 acceptance criteria
#   - Финальный статус заполнен (✅ COMPLETED / ⚠️ PARTIAL / ❌ ABANDONED)
#
# Если что-то пусто — дописывает в recap "🚧 INCOMPLETE: <что>" предупреждение
# (не блокирует — это финальный hook на завершение).

set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

RECAP="$HOME/artvision-data/sync/recaps/${SESSION_ID}.md"
[[ ! -f "$RECAP" ]] && exit 0

# Skip если уже добавляли
grep -q "## 🚧 INCOMPLETE" "$RECAP" && exit 0

ISSUES=()

# 1. Цель сессии
GOAL=$(awk '/^## Цель сессии/{flag=1; next} /^## /{flag=0} flag' "$RECAP" | tr -d '[:space:]')
if [[ -z "$GOAL" || "$GOAL" =~ Незаполнено ]]; then
  ISSUES+=("- Цель сессии не заполнена")
fi

# 2. Deliverables
DELIVERABLES=$(grep -cE '^- \[[xX ]\]' "$RECAP")
if [[ $DELIVERABLES -lt 1 ]]; then
  ISSUES+=("- Нет ни одного deliverable / acceptance в чек-листе")
fi

# 3. Финальный статус
if ! grep -qE '✅ COMPLETED|⚠️ PARTIAL|❌ ABANDONED' "$RECAP"; then
  ISSUES+=("- Финальный статус не заполнен (нужен ✅/⚠️/❌)")
fi

[[ ${#ISSUES[@]} -eq 0 ]] && exit 0

cat >> "$RECAP" <<EOF

---

## 🚧 INCOMPLETE — recap не полный

Stop-hook нашёл пробелы:
$(printf '%s\n' "${ISSUES[@]}")

Заполни перед закрытием сессии. Команда: \`Edit ${RECAP}\`.
Это поле появилось через \`stop-recap-completeness.sh\` (Уровень 4 skill-enforcement).
EOF

exit 0
