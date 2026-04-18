#!/usr/bin/env bash
# start-recap-init.sh — SessionStart hook
# Создаёт artvision-data/sync/recaps/<sessionId>.md из шаблона.
# Claude обязан заполнить "Цель сессии" перед первым Edit/Write/Bash (вне git pull/status).

set -Eeuo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
CWD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null || echo "$PWD")

if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

RECAP_DIR="$HOME/artvision-data/sync/recaps"
RECAP_FILE="$RECAP_DIR/${SESSION_ID}.md"
TEMPLATE="$HOME/.claude/templates/recap-template.md"

mkdir -p "$RECAP_DIR"

if [[ -f "$RECAP_FILE" ]]; then
  echo "📋 Recap (resumed): $RECAP_FILE"
  exit 0
fi

if [[ ! -f "$TEMPLATE" ]]; then
  exit 0
fi

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

sed \
  -e "s|{SESSION_ID}|$SESSION_ID|g" \
  -e "s|{STARTED_AT}|$STARTED_AT|g" \
  -e "s|{CWD}|$CWD|g" \
  "$TEMPLATE" > "$RECAP_FILE"

echo "📋 Recap создан: sync/recaps/${SESSION_ID}.md"
echo "   → Заполни 'Цель сессии' ПЕРЕД первым Edit/Write/Bash (кроме git pull/status)"
