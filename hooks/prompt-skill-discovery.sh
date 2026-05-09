#!/usr/bin/env bash
# prompt-skill-discovery.sh — UserPromptSubmit hook (TF-IDF version)
#
# Bypass: SKILL_DISCOVERY_OFF=1
# Suppress per-session: touch /tmp/skill-discovery-done-{session_id}

set -uo pipefail
[[ "${SKILL_DISCOVERY_OFF:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[[ -z "$PROMPT" || -z "$SESSION_ID" ]] && exit 0
[[ -f "/tmp/skill-discovery-done-${SESSION_ID}" ]] && exit 0
[[ ${#PROMPT} -lt 30 ]] && exit 0

SCRIPT="$HOME/.claude/scripts/skill-discovery-tfidf.py"
if [[ -x "$SCRIPT" ]]; then
  echo "$PROMPT" | python3 "$SCRIPT"
fi
exit 0
