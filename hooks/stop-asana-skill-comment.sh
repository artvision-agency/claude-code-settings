#!/usr/bin/env bash
# stop-asana-skill-comment.sh — Stop hook
#
# Если в текущей сессии вызывались Asana MCP tools (создавали/обновляли задачи) —
# постит в каждую задачу комментарий с аудитом использованных скиллов.
#
# Idempotent: проверяет что в задаче уже нет [skill-audit:<sid>] комментария.

set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

SCRIPT="$HOME/.claude/scripts/asana-skill-comment.py"
[[ ! -x "$SCRIPT" ]] && exit 0

# Run in background — don't block stop. Log to file.
LOG="$HOME/.claude/logs/asana-skill-comment.log"
mkdir -p "$(dirname "$LOG")"
nohup python3 "$SCRIPT" "$SESSION_ID" >>"$LOG" 2>&1 &

exit 0
