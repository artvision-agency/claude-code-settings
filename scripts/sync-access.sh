#!/bin/bash
# Sync clients/*/access.md (клиентские доступы) между аккаунтами через VPS.
# Та же модель что sync-tokens.sh: секреты НЕ в git (gitignore), синк через VPS chmod 600.
# Решает: Claude Андрея/3-го аккаунта не видит access.md (gitignored) → "доступов нет".
#
# Запуск: ~/.claude/scripts/sync-access.sh [push|pull|sync]
#   push  — локальные clients/*/access.md → VPS
#   pull  — VPS → локальные clients/*/access.md (создаёт папки при нужде)
#   sync  — pull, потом push (default)
#
# VPS хранит зеркало в /root/.claude-sync/access/<slug>.md (chmod 600, dir 700).
# Транспорт: rsync over ssh. Mtime-aware (rsync -u: не перетирать новее).

set -euo pipefail

VPS_HOST="root@80.90.181.152"
VPS_DIR="/root/.claude-sync/access"
LOCAL_ROOT="$HOME/artvision-data/clients"
LOCK="/tmp/sync-access.lock.d"
LOG="$HOME/.claude/logs/sync-access.log"
ACTION="${1:-sync}"

mkdir -p "$(dirname "$LOG")"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -d "$LOCK" ] && [ "$(($(date +%s) - $(stat -f %m "$LOCK")))" -gt 120 ]; then
    rmdir "$LOCK" 2>/dev/null; mkdir "$LOCK" 2>/dev/null || { echo "[sync-access] lock busy, skip"; exit 0; }
  else
    echo "[sync-access] already running, skip"; exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

ensure_remote_dir() {
  ssh -o BatchMode=yes "$VPS_HOST" "mkdir -p '$VPS_DIR' && chmod 700 '$VPS_DIR' '$(dirname "$VPS_DIR")'"
}

do_push() {
  ensure_remote_dir
  local n=0
  for f in "$LOCAL_ROOT"/*/access.md; do
    [ -f "$f" ] || continue
    slug=$(basename "$(dirname "$f")")
    rsync -q -u -e "ssh -o BatchMode=yes" "$f" "$VPS_HOST:$VPS_DIR/$slug.md"
    n=$((n+1))
  done
  ssh -o BatchMode=yes "$VPS_HOST" "chmod 600 '$VPS_DIR'/*.md 2>/dev/null || true"
  log "push: OK ($n файлов → VPS)"
}

do_pull() {
  local n=0
  # список remote-файлов
  remote_list=$(ssh -o BatchMode=yes "$VPS_HOST" "ls '$VPS_DIR'/*.md 2>/dev/null || true")
  [ -z "$remote_list" ] && { log "pull: remote пуст, skip"; return 0; }
  while IFS= read -r rf; do
    [ -z "$rf" ] && continue
    slug=$(basename "$rf" .md)
    dest_dir="$LOCAL_ROOT/$slug"
    mkdir -p "$dest_dir"
    rsync -q -u -e "ssh -o BatchMode=yes" "$VPS_HOST:$rf" "$dest_dir/access.md"
    chmod 600 "$dest_dir/access.md" 2>/dev/null || true
    n=$((n+1))
  done <<< "$remote_list"
  log "pull: OK ($n файлов ← VPS)"
}

case "$ACTION" in
  push) do_push ;;
  pull) do_pull ;;
  sync) do_pull; do_push ;;
  *) echo "Usage: $0 [push|pull|sync]"; exit 2 ;;
esac
