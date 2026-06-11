#!/bin/bash
# Автозапуск бота-проверщика показов Я.Директ (строгий сеньор)
# Логи: ~/.claude/logs/ads-verify.log
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"
LOG=~/.claude/logs/ads-verify.log
echo "=== $(date '+%Y-%m-%d %H:%M') ads-verify ===" >> "$LOG"
cd /Users/antonk/artvision-data || exit 1
# --tg: алёрт в Telegram только при CRITICAL/WARN
python3 scripts/ads_show_verifier.py --client avtoworld --tg \
  --html /Users/antonk/artvision-data/clients/avtoworld/ads/cto-expo-2026/ads-status.html \
  >> "$LOG" 2>&1
echo "exit=$? --- $(date '+%H:%M')" >> "$LOG"
