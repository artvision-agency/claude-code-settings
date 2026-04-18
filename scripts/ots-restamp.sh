#!/bin/bash
set -euo pipefail

# Re-stamp Artvision products IP manifest + key source files
# Run: manually after significant product updates, or via cron weekly

PRODUCTS_DIR="/Users/antonk/artvision-data/products"
MANIFEST="$PRODUCTS_DIR/IP-MANIFEST.md"
LOG="/tmp/ots-restamp-$(date +%Y%m%d).log"

# Key source files to stamp individually
FILES=(
  "$PRODUCTS_DIR/direct-radar/direct_radar.py"
  "$PRODUCTS_DIR/seo-pipeline/dispatcher.py"
  "$PRODUCTS_DIR/seo-pipeline/worker.py"
  "$PRODUCTS_DIR/seo-pipeline/scheduler.py"
  "$PRODUCTS_DIR/aivision/README.md"
  "$PRODUCTS_DIR/scout/landing/index.html"
)

echo "$(date '+%Y-%m-%d %H:%M') — OTS restamp started" | tee "$LOG"

# Check if manifest changed since last stamp
if [ -f "$MANIFEST.ots" ]; then
  OLD_HASH=$(ots info "$MANIFEST.ots" 2>/dev/null | grep "File sha256" | awk '{print $4}')
  NEW_HASH=$(shasum -a 256 "$MANIFEST" | awk '{print $1}')
  if [ "$OLD_HASH" = "$NEW_HASH" ]; then
    echo "Manifest unchanged, checking source files..." | tee -a "$LOG"
  else
    echo "Manifest CHANGED — re-stamping" | tee -a "$LOG"
    rm -f "$MANIFEST.ots"
    ots stamp "$MANIFEST" 2>&1 | tee -a "$LOG"
  fi
else
  echo "No existing stamp — creating first" | tee -a "$LOG"
  ots stamp "$MANIFEST" 2>&1 | tee -a "$LOG"
fi

# Stamp changed source files
STAMPED=0
for f in "${FILES[@]}"; do
  [ -f "$f" ] || continue
  if [ -f "$f.ots" ]; then
    OLD=$(ots info "$f.ots" 2>/dev/null | grep "File sha256" | awk '{print $4}')
    NEW=$(shasum -a 256 "$f" | awk '{print $1}')
    if [ "$OLD" != "$NEW" ]; then
      echo "CHANGED: $f — re-stamping" | tee -a "$LOG"
      rm -f "$f.ots"
      ots stamp "$f" 2>&1 | tee -a "$LOG"
      STAMPED=$((STAMPED + 1))
    fi
  else
    echo "NEW: $f — stamping" | tee -a "$LOG"
    ots stamp "$f" 2>&1 | tee -a "$LOG"
    STAMPED=$((STAMPED + 1))
  fi
done

# Git commit if anything changed
cd /Users/antonk/artvision-data
OTS_FILES=$(git status --porcelain -- '*.ots' 2>/dev/null | wc -l | tr -d ' ')
if [ "$OTS_FILES" -gt 0 ]; then
  git add -- '*.ots' products/IP-MANIFEST.md
  git commit -m "chore(ip): restamp $OTS_FILES product files via OpenTimestamps

Co-Authored-By: Claude <noreply@anthropic.com>"
  git push origin main
  echo "Committed + pushed $OTS_FILES .ots files" | tee -a "$LOG"
else
  echo "No changes to stamp" | tee -a "$LOG"
fi

echo "$(date '+%Y-%m-%d %H:%M') — OTS restamp done ($STAMPED files re-stamped)" | tee -a "$LOG"
