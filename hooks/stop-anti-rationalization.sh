#!/bin/bash
# Anti-Rationalization Hook (from Bulletproof pattern)
# Checks if the session ended with rationalization phrases instead of actual fixes

TRANSCRIPT="${CLAUDE_TRANSCRIPT:-}"
if [ -z "$TRANSCRIPT" ]; then
  exit 0
fi

# Check for rationalization patterns in last assistant message
RATIONALIZATIONS=$(echo "$TRANSCRIPT" | grep -ciE '(pre-existing issue|out of scope|follow-up task|works for now|will address later|beyond the scope|separate concern|TODO: fix|known limitation that|leaving as-is)' 2>/dev/null || echo "0")

if [ "$RATIONALIZATIONS" -gt 2 ]; then
  echo "⚠️ Anti-Rationalization: обнаружено $RATIONALIZATIONS фраз-отмазок. Проверь — всё ли доделано, или что-то пропущено?"
fi

exit 0
