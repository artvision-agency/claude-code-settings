#!/usr/bin/env bash
# prompt-compact-recovery.sh — UserPromptSubmit hook
#
# Если есть compact-recovery файл (предыдущий компакшен сохранил контекст) —
# инжектит его в первый prompt после resume.
# Один раз на сессию — потом удаляет файл.

set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

RECOVERY="$HOME/.claude_temp_scripts/compact-recovery-${SESSION_ID}.md"
[[ ! -f "$RECOVERY" ]] && exit 0

# Уже инжектили — есть маркер?
MARKER="$HOME/.claude_temp_scripts/recovery-injected-${SESSION_ID}"
[[ -f "$MARKER" ]] && exit 0

cat <<EOF
[COMPACT RECOVERY] После предыдущего compaction сохранён контекст:

$(cat "$RECOVERY")

Учти открытые задачи и обещания при ответе.
EOF

touch "$MARKER"
exit 0
