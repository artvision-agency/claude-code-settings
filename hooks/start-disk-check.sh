#!/bin/bash
# start-disk-check.sh — SessionStart warn если диск критически забит
# Прецедент: 17.05.2026 — диск 100% (260 MB свободно), узнали по факту.
# Бьёт только если есть проблема — иначе молчит.
set -euo pipefail

# /System/Volumes/Data — реальный data volume на APFS
FREE_GB=$(df -g /System/Volumes/Data 2>/dev/null | awk 'NR==2 {print $4}')
USE_PCT=$(df /System/Volumes/Data 2>/dev/null | awk 'NR==2 {gsub("%","",$5); print $5}')

# Молчим если всё ОК
if [[ -z "$FREE_GB" || -z "$USE_PCT" ]]; then exit 0; fi
if [[ "$FREE_GB" -ge 15 && "$USE_PCT" -lt 90 ]]; then exit 0; fi

# Алёрт-уровни
if [[ "$FREE_GB" -lt 5 || "$USE_PCT" -ge 97 ]]; then
    LEVEL="🚨 CRITICAL"
elif [[ "$FREE_GB" -lt 10 || "$USE_PCT" -ge 93 ]]; then
    LEVEL="⚠️  WARNING"
else
    LEVEL="ℹ️  INFO"
fi

cat <<EOF
═══════════════════════════════════════════
  ${LEVEL}: место на диске
  Свободно: ${FREE_GB} GB · занято ${USE_PCT}%
  Top 3 жирных в \$HOME (быстрый чек):
EOF
du -h -d 1 ~ 2>/dev/null | sort -rh | grep -vE "^[0-9]+(\.[0-9]+)?[KM]?\s+/Users/antonk$" | head -3 | sed 's/^/    /'
cat <<EOF
  Полный аудит: \`du -h -d 1 ~ | sort -rh | head -15\`
═══════════════════════════════════════════

EOF

exit 0
