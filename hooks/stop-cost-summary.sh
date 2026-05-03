#!/usr/bin/env bash
# stop-cost-summary.sh — Stop hook
#
# Суммирует estimated стоимость текущей сессии (Agent calls) и пишет в recap.
# Если >$10 — добавляет ⚠️ предупреждение.

set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

LOG="$HOME/.claude/logs/cost-$(date +%Y-%m).log"
[[ ! -f "$LOG" ]] && exit 0

RECAP="$HOME/artvision-data/sync/recaps/${SESSION_ID}.md"
[[ ! -f "$RECAP" ]] && exit 0

# Skip если уже есть
grep -q "## 💰 Estimated cost" "$RECAP" && exit 0

# Sum cost для этой сессии
TOTAL=$(grep "sid=${SESSION_ID:0:8}" "$LOG" 2>/dev/null | awk -F'cost=\\$' '{sum += $2} END {printf "%.2f", sum+0}')
COUNT=$(grep -c "sid=${SESSION_ID:0:8}" "$LOG" 2>/dev/null || echo 0)

[[ -z "$TOTAL" || "$TOTAL" == "0.00" ]] && exit 0

ALERT=""
# bash float compare via awk
HIGH=$(awk -v t="$TOTAL" 'BEGIN{print (t+0 > 10) ? 1 : 0}')
[[ "$HIGH" == "1" ]] && ALERT="⚠️ Превышен бюджет \$10 на сессию"

cat >> "$RECAP" <<EOF

---

## 💰 Estimated cost

- Agent вызовов: ${COUNT}
- Estimated total: \$${TOTAL}
${ALERT:+- ${ALERT}}

(Heuristic из \`~/.claude/logs/cost-$(date +%Y-%m).log\` — см. post-agent-cost-track.sh)
EOF

exit 0
