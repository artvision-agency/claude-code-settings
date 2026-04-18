#!/bin/bash
set -euo pipefail

# Auto-memory suggest — аналог OpenClaw auto-capture
# Запускается как Stop-хук: анализирует сессию и предлагает что сохранить в memory
# Вдохновлено OpenClaw event lifecycle: after-response → extract durable knowledge

MEMORY_DIR="$HOME/.claude/projects/-Users-antonk/memory"
TIMESTAMP=$(date +%Y-%m-%d)

# Consume stdin (Stop hook sends session JSON)
INPUT=""
if [[ ! -t 0 ]]; then
    INPUT=$(cat 2>/dev/null || true)
fi

# Detect working directory from stdin or fallback
WORK_DIR=$(printf '%s' "$INPUT" | jq -r '.session_cwd // empty' 2>/dev/null || echo "")
if [ -z "$WORK_DIR" ]; then
    WORK_DIR="/Users/antonk/artvision-data"
fi

# 1. Незакоммиченные файлы (что менялось)
CHANGED_FILES=""
STAGED_FILES=""
if [ -d "$WORK_DIR/.git" ] || git -C "$WORK_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    CHANGED_FILES=$(cd "$WORK_DIR" && git diff --name-only HEAD 2>/dev/null || echo "")
    STAGED_FILES=$(cd "$WORK_DIR" && git diff --cached --name-only 2>/dev/null || echo "")
fi

# 2. Последние коммиты этой сессии (за последний час)
RECENT_COMMITS=""
if [ -d "$WORK_DIR/.git" ] || git -C "$WORK_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    RECENT_COMMITS=$(cd "$WORK_DIR" && git log --oneline --since="1 hour ago" 2>/dev/null | head -10 || echo "")
fi

# 3. Новые/изменённые memory файлы (check from artvision-data repo root)
MEMORY_CHANGES=""
REPO_ROOT="/Users/antonk/artvision-data"
if [ -d "$REPO_ROOT/.git" ]; then
    MEMORY_CHANGES=$(cd "$REPO_ROOT" && git diff --name-only HEAD 2>/dev/null | grep -E "\.claude.*memory/" || echo "")
fi

# Build message
MESSAGE="AUTO-MEMORY SUGGEST (OpenClaw-style)

Date: $TIMESTAMP

Session changes:
$(printf '%s' "$RECENT_COMMITS" | sed 's/^/  /' || echo "  (none)")

Changed files:
$(printf '%s\n%s' "$CHANGED_FILES" "$STAGED_FILES" | sort -u | sed '/^$/d' | sed 's/^/  /' || echo "  (none)")

Memory updates:
$(printf '%s' "$MEMORY_CHANGES" | sed 's/^/  /' || echo "  (none)")

CHECK: anything worth saving to memory?
Types: [user] [feedback] [project] [reference]
If nothing new - OK, not all sessions generate memory."

# Output valid JSON for Stop hook — only systemMessage is supported (not hookSpecificOutput)
python3 -c "
import json, sys
msg = sys.stdin.read().strip()
print(json.dumps({'systemMessage': msg}, ensure_ascii=False))
" <<< "$MESSAGE"
