#!/usr/bin/env bash
# NDA-safe запись переговоров: пишем локально → whisper с таймкодами слов →
# глушим NDA-слова из стоп-листа в звуке + вычищаем из текста.
# Записи и стоп-лист — в ЛОКАЛЬНОЙ папке (НЕ в git, NDA-данные).
set -euo pipefail

DIR="${NDA_DIR:-$HOME/Documents/nda-record}"
REC="$DIR/recordings"
STOP="$DIR/stoplist.txt"
MIC="${NDA_MIC:-:1}"          # :1 = Микрофон MacBook Air (см. nda-record.sh devices)
MODEL="${NDA_MODEL:-small}"   # whisper-модель: tiny|base|small|medium
PIDFILE="$DIR/.rec.pid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$REC"
[ -f "$STOP" ] || cat > "$STOP" <<'EOF'
# NDA стоп-лист — по одному слову/токену в строке (фамилии, бренды, названия).
# Эти слова будут ЗАГЛУШЕНЫ в звуке и заменены на ███ в тексте.
# Файл локальный, в git НЕ попадает.
EOF

cmd="${1:-}"
case "$cmd" in
  devices)
    ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 | grep -A20 "AVFoundation"
    ;;
  start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Уже идёт запись (pid $(cat "$PIDFILE"))"; exit 0; fi
    TS="$(date +%Y%m%d-%H%M%S)"
    RAW="$REC/raw-$TS.wav"
    echo "$RAW" > "$DIR/.current"
    nohup ffmpeg -y -f avfoundation -i "$MIC" -ac 1 -ar 16000 "$RAW" >"$DIR/.rec.log" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 2
    if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "🔴 ЗАПИСЬ ПОШЛА → $RAW  (pid $(cat "$PIDFILE"))"
      echo "   Стоп: nda-record.sh stop"
    else
      echo "❌ ffmpeg не стартовал. Лог:"; tail -5 "$DIR/.rec.log"
      echo "   Возможно нужно дать терминалу доступ к Микрофону: Системные настройки → Конфиденциальность → Микрофон."
      rm -f "$PIDFILE"
    fi
    ;;
  stop)
    [ -f "$PIDFILE" ] || { echo "Запись не идёт"; exit 0; }
    PID="$(cat "$PIDFILE")"; kill -INT "$PID" 2>/dev/null || true
    sleep 1; rm -f "$PIDFILE"
    RAW="$(cat "$DIR/.current")"
    echo "⏹  Остановлено: $RAW"; ls -la "$RAW"
    "$0" redact "$RAW"
    ;;
  redact)
    RAW="${2:-$(cat "$DIR/.current")}"
    base="${RAW%.wav}"
    echo "→ Транскрипция (whisper $MODEL, ru, с таймкодами слов)…"
    whisper "$RAW" --model "$MODEL" --language Russian --word_timestamps True \
      --output_format json --output_dir "$REC" --verbose False
    JSON="$REC/$(basename "$base").json"
    python3 "$SCRIPT_DIR/nda_redact.py" "$JSON" "$STOP" "$RAW" "${base}-CLEAN.wav" "${base}-CLEAN.txt"
    echo "✅ Чистый звук:  ${base}-CLEAN.wav  (можно делиться)"
    echo "✅ Чистый текст: ${base}-CLEAN.txt"
    echo "🔒 Сырое:        $RAW  (приватно, НЕ делиться, NDA)"
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      SZ=$(ls -la "$(cat "$DIR/.current")" 2>/dev/null | awk '{print $5}')
      echo "🔴 ИДЁТ ЗАПИСЬ (pid $(cat "$PIDFILE")) → $(cat "$DIR/.current")  [${SZ:-0} байт]"
    else echo "⚪ Записи нет"; fi
    ;;
  *)
    echo "nda-record.sh {start|stop|redact [file]|status|devices}"; exit 1;;
esac
