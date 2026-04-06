#!/bin/bash
# PreCompact: сохраняет критический контекст + длинные промпты перед сжатием
# Предотвращает потерю важной информации при компрессии 200K окна

CONTEXT_FILE="/Users/antonk/artvision-data/.claude_temp_scripts/compact_context.md"
PROMPTS_DIR="/Users/antonk/artvision-data/prompts"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
DATE_SLUG=$(date "+%Y-%m-%d")

mkdir -p "$(dirname "$CONTEXT_FILE")"
mkdir -p "$PROMPTS_DIR"

# --- 1. Сохраняем контекст (как раньше) ---
{
  echo "# Pre-Compact Context Snapshot"
  echo "**Saved:** $TIMESTAMP"
  echo ""

  echo "## Git State"
  cd /Users/antonk/artvision-data 2>/dev/null
  BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
  DIRTY=$(git status --porcelain 2>/dev/null | head -20)
  echo "Branch: $BRANCH"
  if [ -n "$DIRTY" ]; then
    echo "Uncommitted changes:"
    echo '```'
    echo "$DIRTY"
    echo '```'
  else
    echo "Working tree clean."
  fi
  echo ""

  echo "## Recent Commits (last 5)"
  echo '```'
  git log --oneline -5 2>/dev/null || echo "no git history"
  echo '```'
  echo ""

  if [ -f /Users/antonk/artvision-data/.claude_temp_scripts/asana_context.txt ]; then
    echo "## Active Asana Tasks"
    cat /Users/antonk/artvision-data/.claude_temp_scripts/asana_context.txt
    echo ""
  fi

  if [ -f /Users/antonk/artvision-data/sync/SYNC_STATUS.md ]; then
    echo "## Sync Status"
    head -30 /Users/antonk/artvision-data/sync/SYNC_STATUS.md
    echo ""
  fi

} > "$CONTEXT_FILE" 2>/dev/null

# --- 2. Извлекаем длинные промпты пользователя из текущей сессии ---
# Находим текущий session ID по последнему изменённому .jsonl
SESSION_DIR="/Users/antonk/.claude/projects/-Users-antonk"
CURRENT_SESSION=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -n "$CURRENT_SESSION" ]; then
  SESSION_ID=$(basename "$CURRENT_SESSION" .jsonl)
  PROMPTS_FILE="$PROMPTS_DIR/${DATE_SLUG}_session_${SESSION_ID:0:8}.md"

  # Извлекаем все user messages >500 символов (это промпты, не короткие команды)
  # ВАЖНО: Python-скрипт вынесен в отдельный файл, т.к. heredoc ломается когда
  # JSONL-сессия содержит текст с heredoc-маркером (этот хук записывается в сессию)
  python3 /Users/antonk/.claude/scripts/extract-session-prompts.py \
    "$CURRENT_SESSION" "$PROMPTS_FILE" "$TIMESTAMP"

  # Auto-commit prompts to git
  cd /Users/antonk/artvision-data 2>/dev/null
  if [ -d "$PROMPTS_DIR" ] && [ "$(ls -A "$PROMPTS_DIR" 2>/dev/null)" ]; then
    git add "$PROMPTS_DIR"/*.md 2>/dev/null
    git diff --cached --quiet 2>/dev/null || {
      git commit -m "chore: save session prompts before compact $(date +%Y-%m-%d_%H:%M)

Co-Authored-By: Claude <noreply@anthropic.com>" 2>/dev/null
    }
  fi
fi

echo "[pre-compact] Контекст сохранён в $CONTEXT_FILE"
echo "[pre-compact] Промпты сохранены в $PROMPTS_DIR/"
echo ""
echo "⚠️ AFTER COMPACTION — MANDATORY:"
echo "1. Read $CONTEXT_FILE"
echo "2. TaskCreate for EVERY pending item from summary"
echo "3. Check TODO.md files for open tasks"

# Count pending tasks for visibility
for todo in /Users/antonk/artvision-data/TODO.md /Users/antonk/artvision-tg-bot/TODO.md /Users/antonk/devops-agent/TODO.md; do
  if [ -f "$todo" ]; then
    COUNT=$(grep -c '^\- \[ \]' "$todo" 2>/dev/null || true)
    COUNT=$(echo "$COUNT" | tr -d '[:space:]')
    if [ -n "$COUNT" ] && [ "$COUNT" != "0" ]; then
      echo "📋 $(basename "$(dirname "$todo")"): $COUNT pending"
    fi
  fi
done

exit 0
