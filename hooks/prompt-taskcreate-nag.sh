#!/usr/bin/env bash
# UserPromptSubmit hook: if there are pending tasks in TODO.md AND no TaskCreate
# has been called yet in this session, inject an imperative reminder ahead of
# the user's prompt. Self-disables after first TaskCreate or after 10 turns.
#
# Layer 1 of "TaskCreate enforcement". Complements SessionStart hooks
# (start-todo-tasks.sh, start-todo-taskcreate.sh) which lose salience after
# a few turns.

set -uo pipefail

input="$(cat || true)"
session_id=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")

# 1. Count pending tasks across all TODO files
pending=0
for f in "$HOME/artvision-data/TODO.md" \
         "$HOME/artvision-data/presale/TODO.md" \
         "$HOME/artvision-data/products/TODO.md" \
         "$HOME/artvision-tg-bot/TODO.md" \
         "$HOME/devops-agent/TODO.md"; do
  [ -f "$f" ] || continue
  n=$(grep -cE '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\]' "$f" 2>/dev/null | tr -d ' ' || echo 0)
  pending=$((pending + ${n:-0}))
done
[ "$pending" -eq 0 ] && exit 0

# 2. Locate session transcript
transcript=""
if [ -n "$session_id" ]; then
  transcript=$(find "$HOME/.claude/projects" -maxdepth 3 -name "${session_id}.jsonl" 2>/dev/null | head -1)
fi

# 3. Skip if TaskCreate already fired this session
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  if grep -q '"name":"TaskCreate"' "$transcript" 2>/dev/null; then
    exit 0
  fi
  # Stop nagging after 10 user prompts
  turns=$(grep -c '"type":"user"' "$transcript" 2>/dev/null | tr -d ' ' || echo 0)
  if [ "${turns:-0}" -gt 10 ]; then
    exit 0
  fi
fi

# 4. Gather top-5 HIGH priority pending, fallback to first 5 pending
top=""
for f in "$HOME/artvision-data/TODO.md" \
         "$HOME/artvision-data/presale/TODO.md" \
         "$HOME/artvision-data/products/TODO.md" \
         "$HOME/artvision-tg-bot/TODO.md" \
         "$HOME/devops-agent/TODO.md"; do
  [ -f "$f" ] || continue
  top="$top$(grep -E '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\].*priority:high' "$f" 2>/dev/null | head -5)
"
done
top=$(printf '%s' "$top" | awk 'NF' | head -5)
if [ -z "$top" ]; then
  for f in "$HOME/artvision-data/TODO.md" \
           "$HOME/artvision-data/presale/TODO.md" \
           "$HOME/artvision-data/products/TODO.md"; do
    [ -f "$f" ] || continue
    top=$(grep -E '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\]' "$f" 2>/dev/null | head -5)
    [ -n "$top" ] && break
  done
fi

# 5. Emit JSON with additionalContext
python3 - "$pending" "$top" <<'PY'
import json, sys
pending, top = sys.argv[1], sys.argv[2]
msg = f"""⛔ STILL NO TaskCreate in this session — but {pending} pending items are in TODO.

BEFORE answering the user's latest prompt, call TaskCreate for these top items:

{top}

(This reminder auto-fires on every UserPromptSubmit until TaskCreate is called, for up to 10 turns.)"""
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg
    }
}))
PY
