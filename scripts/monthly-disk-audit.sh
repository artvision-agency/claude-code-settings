#!/bin/bash
# monthly-disk-audit.sh — раз в месяц TG-сводка top-10 жирных папок + дельта vs прошлый месяц
# Установлено 17.05.2026 после disk-full инцидента.
set -euo pipefail

LOG=~/.claude/logs/disk-audit.log
STATE=~/.claude/logs/disk-audit-state.json
mkdir -p ~/.claude/logs
ts() { date '+%Y-%m-%d %H:%M:%S'; }

FREE_GB=$(df -g /System/Volumes/Data 2>/dev/null | awk 'NR==2 {print $4}')
USE_PCT=$(df /System/Volumes/Data 2>/dev/null | awk 'NR==2 {gsub("%","",$5); print $5}')

# Top-10 директорий в $HOME, в KB для машинной обработки
TOP_RAW=$(du -k -d 1 ~ 2>/dev/null | sort -rn | head -11 | grep -v "^[0-9]*	/Users/antonk$" | head -10)

# Сводка для TG (human-readable)
TG_BODY="📊 Disk audit $(date '+%Y-%m-%d')

Свободно: ${FREE_GB} GB · занято ${USE_PCT}%

Top 10 папок в \$HOME:
"
while IFS=$'\t' read -r kb path; do
    human=$(du -h -d 0 "$path" 2>/dev/null | awk '{print $1}')
    name=$(basename "$path")
    TG_BODY+="  ${human}  ${name}
"
done <<< "$TOP_RAW"

# Дельта vs прошлый месяц
if [[ -f "$STATE" ]]; then
    PREV_FREE=$(python3 -c "import json; print(json.load(open('$STATE'))['free_gb'])" 2>/dev/null || echo "?")
    DELTA=$((FREE_GB - PREV_FREE)) 2>/dev/null || DELTA="?"
    TG_BODY+="
Дельта vs прошлый месяц: ${DELTA} GB свободного"
fi

# Сохранить state
python3 -c "
import json
json.dump({'date': '$(date +%Y-%m-%d)', 'free_gb': ${FREE_GB}, 'use_pct': ${USE_PCT}}, open('$STATE','w'))
" 2>/dev/null || true

echo "[$(ts)] sending TG audit (free=${FREE_GB}GB, use=${USE_PCT}%)" >> "$LOG"

# Отправка в TG (anton private)
if [[ -x ~/.claude/scripts/tg-send.sh ]]; then
    ~/.claude/scripts/tg-send.sh anton "$TG_BODY" 2>&1 | tail -3 >> "$LOG" || echo "[$(ts)] TG send failed" >> "$LOG"
else
    echo "[$(ts)] tg-send.sh not found, dumping to log:" >> "$LOG"
    echo "$TG_BODY" >> "$LOG"
fi

exit 0
