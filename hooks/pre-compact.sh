#!/bin/bash
# PreCompact: сохраняет критический контекст перед сжатием
# Предотвращает потерю важной информации при компрессии 200K окна

CONTEXT_FILE="/Users/antonk/artvision-data/.claude_temp_scripts/compact_context.md"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")

mkdir -p "$(dirname "$CONTEXT_FILE")"

# Собираем текущее состояние
{
  echo "# Pre-Compact Context Snapshot"
  echo "**Saved:** $TIMESTAMP"
  echo ""

  # Git: текущая ветка и незакоммиченные изменения
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

  # Последние коммиты (контекст работы)
  echo "## Recent Commits (last 5)"
  echo '```'
  git log --oneline -5 2>/dev/null || echo "no git history"
  echo '```'
  echo ""

  # Активные задачи Asana (если есть кэш)
  if [ -f /Users/antonk/artvision-data/.claude_temp_scripts/asana_context.txt ]; then
    echo "## Active Asana Tasks"
    cat /Users/antonk/artvision-data/.claude_temp_scripts/asana_context.txt
    echo ""
  fi

  # Текущий SYNC_STATUS
  if [ -f /Users/antonk/artvision-data/sync/SYNC_STATUS.md ]; then
    echo "## Sync Status"
    head -30 /Users/antonk/artvision-data/sync/SYNC_STATUS.md
    echo ""
  fi

} > "$CONTEXT_FILE" 2>/dev/null

echo "[pre-compact] Контекст сохранён в $CONTEXT_FILE"
echo "[pre-compact] После compact используйте: Read $CONTEXT_FILE для восстановления контекста"

exit 0
