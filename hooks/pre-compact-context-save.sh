#!/usr/bin/env bash
# pre-compact-context-save.sh — PreCompact hook
#
# Перед компакшеном сохраняет:
#   - текущую цель сессии (из recap.md)
#   - открытые TaskCreate (через TaskList — но из transcript)
#   - последние 5 prompts пользователя
#   - незаконченные обещания (фразы "сделаю", "доделаю", "потом", "после")
#
# Сохраняет в ~/.claude_temp_scripts/compact-recovery-{sid}.md
# UserPromptSubmit hook после resume может прочитать и инжектить как контекст.

set -uo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
[[ ! -f "$TRANSCRIPT" ]] && exit 0

OUT_DIR="$HOME/.claude_temp_scripts"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/compact-recovery-${SESSION_ID}.md"

# 1. Goal из recap
RECAP="$HOME/artvision-data/sync/recaps/${SESSION_ID}.md"
GOAL=""
if [[ -f "$RECAP" ]]; then
  GOAL=$(awk '/^## Цель сессии/{flag=1; next} /^## /{flag=0} flag {print}' "$RECAP" | head -3 | tr '\n' ' ')
fi

# 2. Последние user prompts (5)
USER_PROMPTS=$(jq -r 'select(.message.role=="user") | .message.content | if type=="array" then (map(select(.type=="text") | .text) | join(" ")) else . end' "$TRANSCRIPT" 2>/dev/null \
  | grep -v '^<' | tail -5 | sed 's/^/  - /')

# 3. Open TaskCreate (через парсинг tool_use)
OPEN_TASKS=$(jq -r '.message.content[]? | select(.type=="tool_use" and .name=="TaskCreate") | .input.subject' "$TRANSCRIPT" 2>/dev/null | tail -10 | sed 's/^/  - [ ] /')

# 4. Phrases-обещания
PROMISES=$(jq -r '.message.content[]? | select(.type=="text") | .text' "$TRANSCRIPT" 2>/dev/null \
  | grep -oE '(сделаю|доделаю|допилю|допишу|допущу|после этого|потом|следующий шаг)[^.!?]*[.!?]' \
  | tail -8 | sed 's/^/  - /')

cat > "$OUT" <<EOF
# Compaction Recovery — ${SESSION_ID}

Сохранено: $(date +%FT%T)

## 🎯 Цель
${GOAL:-—}

## 📥 Последние 5 user prompts
${USER_PROMPTS:-—}

## 📋 Открытые TaskCreate
${OPEN_TASKS:-—}

## 💬 Невыполненные обещания
${PROMISES:-—}

---
Файл читается UserPromptSubmit-хуком после resume.
EOF

exit 0
