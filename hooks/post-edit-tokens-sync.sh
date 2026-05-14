#!/bin/bash
# PostToolUse Edit|Write hook — auto-push tokens.json на VPS при изменении.
# Триггер: $CLAUDE_FILE_PATH либо $1 содержит "tokens.json".

set -u
FILE="${1:-${CLAUDE_FILE_PATH:-}}"
[ -n "$FILE" ] || exit 0

# Только для tokens.json в artvision-data
case "$FILE" in
  */artvision-data/tokens.json|*/tokens.json)
    SCRIPT="$HOME/.claude/scripts/sync-tokens.sh"
    [ -x "$SCRIPT" ] || exit 0
    (
      timeout 15 "$SCRIPT" push 2>&1 | tail -1
    ) </dev/null >>"$HOME/.claude/logs/sync-tokens.log" 2>&1 &
    disown 2>/dev/null || true
    ;;
esac

exit 0
