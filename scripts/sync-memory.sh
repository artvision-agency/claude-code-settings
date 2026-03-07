#!/bin/bash
# Синхронизация Claude Code авто-памяти между аккаунтами через git
# Запуск: ~/.claude/scripts/sync-memory.sh [push|pull]

set -e

MEMORY_SRC="$HOME/.claude/projects/-Users-antonk/memory"
SYNC_DST="$HOME/artvision-data/.claude/memory-sync"
REPO="$HOME/artvision-data"

case "${1:-push}" in
  push)
    echo "📤 Копирую memory → artvision-data/.claude/memory-sync/"
    mkdir -p "$SYNC_DST"
    rsync -av --delete "$MEMORY_SRC/" "$SYNC_DST/"
    cd "$REPO"
    git add .claude/memory-sync/
    if git diff --cached --quiet; then
      echo "✅ Нет изменений в памяти"
    else
      git commit -m "sync: memory $(date +%Y-%m-%d_%H:%M)

Co-Authored-By: Claude <noreply@anthropic.com>"
      git push
      echo "✅ Память запушена"
    fi
    ;;
  pull)
    echo "📥 Подтягиваю память из git"
    cd "$REPO"
    git pull --ff-only
    if [ -d "$SYNC_DST" ]; then
      mkdir -p "$MEMORY_SRC"
      rsync -av "$SYNC_DST/" "$MEMORY_SRC/"
      echo "✅ Память обновлена из git"
    else
      echo "⚠️ $SYNC_DST не найден в репо"
    fi
    ;;
  *)
    echo "Использование: sync-memory.sh [push|pull]"
    exit 1
    ;;
esac
