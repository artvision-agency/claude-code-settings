#!/usr/bin/env bash
# UserPromptSubmit hook: if there are pending tasks in the CURRENT-CONTEXT
# TODO.md AND no TaskCreate has been called yet in this session, inject an
# imperative reminder ahead of the user's prompt.
# Self-disables after first TaskCreate or after 10 turns.
#
# Layer 1 of "TaskCreate enforcement". Complements SessionStart hooks
# (start-todo-tasks.sh, start-todo-taskcreate.sh) which lose salience after
# a few turns.
#
# 2026-04-27: фильтр по контексту сессии (cwd → todo-route.sh). Раньше брало
# top-5 high со ВСЕХ 5 TODO — спамило задачами не из темы текущей сессии.

set -uo pipefail

LIB="${HOME}/.claude/scripts/lib/todo-route.sh"
[ -f "$LIB" ] || exit 0
# shellcheck source=/dev/null
source "$LIB"

input="$(cat || true)"
session_id=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
cwd_in=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null || echo "")
[ -z "$cwd_in" ] && cwd_in="${PWD:-$HOME}"

mapping="$(todo_for_cwd "$cwd_in")"
TODO="${mapping%%$'\t'*}"
CTX="${mapping##*$'\t'}"

# home / нет TODO → silent (не пинаем TaskCreate на нейтральной сессии)
[ "$CTX" = "home" ] && exit 0
[ -f "$TODO" ] || exit 0

# 1. Pending tasks ТОЛЬКО в текущем контексте
pending=$(grep -cE '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\]' "$TODO" 2>/dev/null | tr -d ' ' || echo 0)
[ "${pending:-0}" -eq 0 ] && exit 0

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

# 4. Top-5 high из текущего контекста, fallback — первые 5 pending
top=$(grep -E '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\].*priority:high' "$TODO" 2>/dev/null | head -5)
if [ -z "$top" ]; then
  top=$(grep -E '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\]' "$TODO" 2>/dev/null | head -5)
fi
[ -z "$top" ] && exit 0

# 5. Emit JSON with additionalContext
python3 - "$pending" "$top" "$CTX" <<'PY'
import json, sys
pending, top, ctx = sys.argv[1], sys.argv[2], sys.argv[3]
msg = f"""⛔ STILL NO TaskCreate in this session — but {pending} pending items are in TODO ({ctx}).

BEFORE answering the user's latest prompt, call TaskCreate for these top items (контекст: {ctx}):

{top}

(This reminder auto-fires on every UserPromptSubmit until TaskCreate is called, for up to 10 turns. Только текущий контекст сессии.)"""
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg
    }
}))
PY
