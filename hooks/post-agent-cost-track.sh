#!/usr/bin/env bash
# post-agent-cost-track.sh — PostToolUse Agent
#
# Логирует каждый Agent tool вызов с estimated cost ($/1M tokens × tokens).
# При закрытии сессии Stop hook суммирует и алертит если бюджет превышен.

set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[[ "$TOOL_NAME" != "Agent" ]] && exit 0

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

SUBAGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // "general-purpose"' 2>/dev/null)
DESC=$(echo "$INPUT" | jq -r '.tool_input.description // ""' 2>/dev/null | head -c 80)

# Estimated cost (rough heuristic — Opus avg ~$0.40 per agent call)
COST_USD="0.40"
case "$SUBAGENT" in
  general-purpose) COST_USD="0.30" ;;
  Explore) COST_USD="0.10" ;;
  ui-visual-validator|accessibility-tester) COST_USD="0.50" ;;
  competitive-analyst|product-manager|seo-analyzer|ui-designer) COST_USD="0.45" ;;
  frontend-developer|backend-developer|frontend-design) COST_USD="0.40" ;;
esac

LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/cost-$(date +%Y-%m).log"

echo "$(date +%FT%T) sid=${SESSION_ID:0:8} agent=${SUBAGENT} cost=\$${COST_USD} desc=\"${DESC}\"" >> "$LOG"

exit 0
