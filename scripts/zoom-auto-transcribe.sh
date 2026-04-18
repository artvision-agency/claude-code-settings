#!/usr/bin/env bash
# Автотранскрибация Zoom-записей через Groq Whisper API
# Watch: ~/Documents/Zoom/**/audio*.m4a
# Out: ~/transcripts/<slug>-YYYY-MM-DD.{json,txt}
# Marker: рядом с аудио файл .transcribed
#
# Запуск: LaunchAgent pro.artvision.zoom-transcribe (WatchPaths)
# Ручной: ~/.claude/scripts/zoom-auto-transcribe.sh

set -euo pipefail

ZOOM_DIR="$HOME/Documents/Zoom"
OUT_DIR="$HOME/transcripts"
LOG="$HOME/.claude/logs/zoom-transcribe.log"
TOKENS="$HOME/artvision-data/tokens.json"

mkdir -p "$OUT_DIR" "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

[ ! -f "$TOKENS" ] && { log "ERROR: tokens.json not found"; exit 1; }

GROQ_KEY=$(python3 -c "import json,sys; print(json.load(open('$TOKENS'))['groq']['api_key'])" 2>/dev/null || true)
[ -z "$GROQ_KEY" ] && { log "ERROR: groq.api_key missing in tokens.json"; exit 1; }

# Только файлы за последние 3 дня (защита от backfill старых записей)
# Для бэкфилла старых — запускать вручную с AV_ZOOM_BACKFILL=1
MTIME_FLAG="-mtime -3"
[ "${AV_ZOOM_BACKFILL:-0}" = "1" ] && MTIME_FLAG=""

find "$ZOOM_DIR" -type f -name "audio*.m4a" $MTIME_FLAG 2>/dev/null | while IFS= read -r audio; do
  marker="${audio}.transcribed"
  [ -f "$marker" ] && continue

  # slug из имени папки: YYYY-MM-DD + первое значимое слово
  dir=$(dirname "$audio")
  folder=$(basename "$dir")
  date_part=$(echo "$folder" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' || date +%Y-%m-%d)
  slug=$(echo "$folder" | sed -E 's/^[0-9-]+ [0-9.]+ //; s/[^A-Za-zА-Яа-я0-9]+/-/g; s/^-+|-+$//g' | cut -c1-40)
  [ -z "$slug" ] && slug="zoom"
  out_base="$OUT_DIR/${slug}-${date_part}"

  # Если уже есть — пропустить (но marker мог отсутствовать)
  if [ -f "${out_base}.json" ]; then
    touch "$marker"
    log "SKIP (exists): $audio -> ${out_base}.json"
    continue
  fi

  log "TRANSCRIBE: $audio"

  # Размер файла (Groq limit 25MB для free tier)
  size=$(stat -f%z "$audio" 2>/dev/null || echo 0)
  if [ "$size" -gt 26214400 ]; then
    log "WARN: $audio > 25MB ($size bytes), пропуск — нужна разбивка через ffmpeg"
    touch "${audio}.too-large"
    continue
  fi

  http_code=$(curl -sS -w "%{http_code}" -o "${out_base}.json" \
    -X POST "https://api.groq.com/openai/v1/audio/transcriptions" \
    -H "Authorization: Bearer $GROQ_KEY" \
    -F "file=@${audio}" \
    -F "model=whisper-large-v3-turbo" \
    -F "language=ru" \
    -F "response_format=verbose_json" \
    -F "temperature=0" 2>>"$LOG" || echo "000")

  if [ "$http_code" != "200" ]; then
    log "ERROR: Groq HTTP $http_code for $audio"
    rm -f "${out_base}.json"
    continue
  fi

  # Извлечь text → .txt
  python3 -c "
import json
d = json.load(open('${out_base}.json'))
open('${out_base}.txt','w').write(d.get('text',''))
print(len(d.get('text','')))
" >> "$LOG" 2>&1 || log "WARN: text extract failed for $audio"

  touch "$marker"
  log "DONE: ${out_base}.txt"

  # Уведомление в TG (если настроено)
  if [ -f "$HOME/.claude/scripts/tg-notify.sh" ]; then
    "$HOME/.claude/scripts/tg-notify.sh" "🎙 Zoom транскрибация: ${slug}-${date_part}" 2>/dev/null || true
  fi
done

log "scan complete"
