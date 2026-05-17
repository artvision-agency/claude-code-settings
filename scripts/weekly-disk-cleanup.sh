#!/bin/bash
# weekly-disk-cleanup.sh — runs weekly via launchctl pro.artvision.disk-cleanup
# Frees disk in ~/.claude/ to prevent crashes (precedent: 26.04 — 97% disk + OOM = sessions died).
set -euo pipefail

LOG=~/.claude/logs/disk-cleanup.log
mkdir -p ~/.claude/logs
ts() { date '+%Y-%m-%d %H:%M:%S'; }

DISK_BEFORE=$(df -g "$HOME" | awk 'NR==2 {print $4}')
echo "[$(ts)] === START disk-cleanup, free=${DISK_BEFORE}GB ===" >> "$LOG"

# 1. Old session JSONL >14 days
N1=$(find ~/.claude/projects/-Users-antonk/ -maxdepth 1 -name '*.jsonl' -mtime +14 -type f 2>/dev/null | wc -l | tr -d ' ')
find ~/.claude/projects/-Users-antonk/ -maxdepth 1 -name '*.jsonl' -mtime +14 -type f -delete 2>/dev/null || true
echo "[$(ts)] removed $N1 stale JSONL (>14d)" >> "$LOG"

# 2. Old Claude CLI binaries (keep current)
N2=$(find ~/.claude/downloads -maxdepth 1 -name 'claude-*-darwin-arm64' -mtime +7 -type f 2>/dev/null | wc -l | tr -d ' ')
find ~/.claude/downloads -maxdepth 1 -name 'claude-*-darwin-arm64' -mtime +7 -type f -delete 2>/dev/null || true
echo "[$(ts)] removed $N2 old CLI binaries" >> "$LOG"

# 3. Truncate huge stderr logs >5MB (keep last 1MB)
for f in ~/.claude/logs/*.stderr.log ~/.claude/logs/*.err.log; do
  [ -f "$f" ] || continue
  size=$(stat -f %z "$f" 2>/dev/null || echo 0)
  if [ "$size" -gt 5242880 ]; then
    tail -c 1048576 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    echo "[$(ts)] truncated $(basename "$f") (was ${size}B)" >> "$LOG"
  fi
done

# 4. Old file-history >30 days
N4=$(find ~/.claude/file-history -maxdepth 1 -mtime +30 -type f 2>/dev/null | wc -l | tr -d ' ')
find ~/.claude/file-history -maxdepth 1 -mtime +30 -type f -delete 2>/dev/null || true
echo "[$(ts)] removed $N4 stale file-history entries (>30d)" >> "$LOG"

# 5. Old telemetry >30 days
N5=$(find ~/.claude/telemetry -maxdepth 1 -mtime +30 -type f 2>/dev/null | wc -l | tr -d ' ')
find ~/.claude/telemetry -maxdepth 1 -mtime +30 -type f -delete 2>/dev/null || true
echo "[$(ts)] removed $N5 stale telemetry entries (>30d)" >> "$LOG"

# 6. ~/Library/Caches и ~/.cache — приложения сами пересоздают
# Добавлено 17.05.2026 после disk-full инцидента (260 MB свободно)
CACHE_LIB_BEFORE=$(du -sk ~/Library/Caches 2>/dev/null | awk '{print $1}')
CACHE_HOME_BEFORE=$(du -sk ~/.cache 2>/dev/null | awk '{print $1}')
rm -rf ~/Library/Caches/* 2>/dev/null || true
rm -rf ~/.cache/* 2>/dev/null || true
echo "[$(ts)] cleaned ~/Library/Caches (was ${CACHE_LIB_BEFORE}KB) + ~/.cache (was ${CACHE_HOME_BEFORE}KB)" >> "$LOG"

DISK_AFTER=$(df -g "$HOME" | awk 'NR==2 {print $4}')
FREED=$((DISK_AFTER - DISK_BEFORE))
echo "[$(ts)] === END free=${DISK_AFTER}GB (freed ~${FREED}GB) ===" >> "$LOG"

exit 0
