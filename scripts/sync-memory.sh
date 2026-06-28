#!/bin/bash
# Синхронизация Claude Code авто-памяти между аккаунтами через git
# Запуск: ~/.claude/scripts/sync-memory.sh [sync|push|pull]
# По умолчанию (без аргументов) = sync = pull + push

set -euo pipefail

# --- mutual lock (macOS: mkdir-atomic, нет flock) ---
_GSLOCK=/tmp/artvision-git-sync.lock
if ! mkdir "$_GSLOCK" 2>/dev/null; then
  # stale > 5 мин → забрать
  if find "$_GSLOCK" -maxdepth 0 -mmin +5 2>/dev/null | grep -q .; then
    rmdir "$_GSLOCK" 2>/dev/null; mkdir "$_GSLOCK" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi
trap 'rmdir "$_GSLOCK" 2>/dev/null' EXIT
# --- /lock ---

MEMORY_SRC="$HOME/.claude/projects/-Users-antonk/memory"
SYNC_DST="$HOME/artvision-data/.claude/memory-sync"
RULES_SRC="$HOME/.claude/rules"
RULES_DST="$HOME/artvision-data/.claude/rules-global"
REPO="$HOME/artvision-data"

do_pull() {
  echo "📥 Pull: git → локальные memory + rules"
  cd "$REPO"
  # DATA-LOSS-SAFE (2026-06-20, инцидент потери файлов/токена yail307):
  # БЫЛО: ff-only || pull --rebase — fallback на rebase отвязывал локальные коммиты → dangling.
  # СТАЛО: ff-only; если не прошёл — merge (--no-rebase) ТОЛЬКО при чистом дереве.
  #   Грязное дерево (WIP другой сессии в artvision-data) → пропустить pull, не трогать данные.
  if ! git pull --ff-only 2>/dev/null; then
    if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
      git -c core.symlinks=false pull --no-rebase --no-edit \
        || { git merge --abort 2>/dev/null || true; echo "⚠️  merge-конфликт — merge --abort, локальные коммиты целы"; }
    else
      echo "⚠️  дерево грязное — pull пропущен (rebase/stash не делаем, данные целы)"
    fi
  fi
  if [ -d "$SYNC_DST" ]; then
    mkdir -p "$MEMORY_SRC"
    rsync -a "$SYNC_DST/" "$MEMORY_SRC/"
  fi
  if [ -d "$RULES_DST" ]; then
    mkdir -p "$RULES_SRC"
    rsync -a "$RULES_DST/" "$RULES_SRC/"
  fi
  echo "✅ Pull done"
}

do_push() {
  echo "📤 Push: локальные memory + rules → git"
  mkdir -p "$SYNC_DST" "$RULES_DST"
  rsync -a --delete "$MEMORY_SRC/" "$SYNC_DST/"
  rsync -a --delete "$RULES_SRC/" "$RULES_DST/"
  cd "$REPO"
  git add .claude/memory-sync/ .claude/rules-global/
  if git diff --cached --quiet; then
    echo "✅ Нет изменений"
  else
    git commit -m "sync: memory+rules $(date +%Y-%m-%d_%H:%M)

Co-Authored-By: Claude <noreply@anthropic.com>"
    git push
    echo "✅ Запушено"
  fi
}

case "${1:-sync}" in
  sync)  do_pull && do_push ;;
  push)  do_push ;;
  pull)  do_pull ;;
  *)     echo "Использование: sync-memory.sh [sync|push|pull]"; exit 1 ;;
esac
