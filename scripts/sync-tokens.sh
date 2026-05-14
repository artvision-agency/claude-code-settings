#!/bin/bash
# Sync ~/artvision-data/tokens.json между устройствами через VPS.
# Запуск: ~/.claude/scripts/sync-tokens.sh [push|pull|sync]
#   push  — локальный → VPS (если локальный новее или remote отсутствует)
#   pull  — VPS → локальный (если remote новее)
#   sync  — pull, потом push (default)
#
# VPS хранит tokens.json в /root/.claude-sync/tokens.json (chmod 600, 700 dir).
# Решение «кто новее» — по mtime. Если remote новее на >2 сек → pull. Если local новее → push.
# Lock-файл предотвращает race conditions.

set -euo pipefail

VPS_HOST="root@80.90.181.152"
VPS_PATH="/root/.claude-sync/tokens.json"
LOCAL="$HOME/artvision-data/tokens.json"
LOCK="/tmp/sync-tokens.lock.d"
LOG="$HOME/.claude/logs/sync-tokens.log"
ACTION="${1:-sync}"

mkdir -p "$(dirname "$LOG")"
# macOS-compat lock: mkdir is atomic. Stale lock >120s — снимаем.
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -d "$LOCK" ] && [ "$(($(date +%s) - $(stat -f %m "$LOCK")))" -gt 120 ]; then
    rmdir "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null || { echo "[sync-tokens] lock busy, skip"; exit 0; }
  else
    echo "[sync-tokens] already running, skip"; exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

mtime_local() {
  if [ -f "$LOCAL" ]; then stat -f %m "$LOCAL"; else echo "0"; fi
}
mtime_remote() {
  ssh -o ConnectTimeout=5 -o BatchMode=yes "$VPS_HOST" \
    "stat -c %Y '$VPS_PATH' 2>/dev/null || echo 0" 2>/dev/null || echo "0"
}
sha_local() {
  if [ -f "$LOCAL" ]; then shasum -a 256 "$LOCAL" | awk '{print $1}'; else echo "none"; fi
}
sha_remote() {
  ssh -o ConnectTimeout=5 -o BatchMode=yes "$VPS_HOST" \
    "sha256sum '$VPS_PATH' 2>/dev/null | awk '{print \$1}' || echo none" 2>/dev/null || echo "none"
}

do_push() {
  local sl sr
  sl=$(sha_local); sr=$(sha_remote)
  if [ "$sl" = "$sr" ]; then
    log "push: identical (sha=$sl), skip"
    return 0
  fi
  if [ ! -f "$LOCAL" ]; then
    log "push: local missing, abort"
    return 1
  fi
  ssh -o BatchMode=yes "$VPS_HOST" "mkdir -p $(dirname $VPS_PATH) && chmod 700 $(dirname $VPS_PATH)"
  scp -q -o BatchMode=yes "$LOCAL" "$VPS_HOST:$VPS_PATH"
  ssh -o BatchMode=yes "$VPS_HOST" "chmod 600 $VPS_PATH"
  log "push: OK (sha=$sl)"
}

do_pull() {
  local ml mr sl sr
  ml=$(mtime_local); mr=$(mtime_remote)
  sl=$(sha_local); sr=$(sha_remote)
  if [ "$sr" = "none" ]; then
    log "pull: remote missing, skip"
    return 0
  fi
  if [ "$sl" = "$sr" ]; then
    log "pull: identical (sha=$sl), skip"
    return 0
  fi
  # remote новее как минимум на 2 секунды → пуллим. иначе локальный считаем новее.
  if [ "$mr" -le "$((ml + 2))" ]; then
    log "pull: local is newer or equal (local=$ml remote=$mr), skip"
    return 0
  fi
  cp "$LOCAL" "$LOCAL.bak.$(date +%s)" 2>/dev/null || true
  scp -q -o BatchMode=yes "$VPS_HOST:$VPS_PATH" "$LOCAL.tmp"
  mv "$LOCAL.tmp" "$LOCAL"
  chmod 600 "$LOCAL"
  log "pull: OK (sha=$sr)"
}

case "$ACTION" in
  push) do_push ;;
  pull) do_pull ;;
  sync) do_pull; do_push ;;
  *) echo "Usage: $0 [push|pull|sync]"; exit 2 ;;
esac
