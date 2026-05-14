#!/bin/bash
# Burn-in subtitles + loudness normalization to -14 LUFS (YouTube standard)
#
# Usage:
#   burn-and-normalize.sh INPUT.mp4 SUBS.srt OUTPUT.mp4
#
# Subtitle params (zero-tweak — Антон 2026-05-12):
#   FontSize=24, Bold=1, BorderStyle=4 (box), MarginV=900 (above PiP)
set -euo pipefail

INPUT="$1"
SUBS="$2"
OUTPUT="$3"

if [[ ! -f "$INPUT" || ! -f "$SUBS" ]]; then
  echo "Usage: $0 INPUT.mp4 SUBS.srt OUTPUT.mp4" >&2
  exit 1
fi

# Convert SRT to ASS with proper PlayRes 1080x1920 (libass scales font incorrectly with force_style+SRT on macOS)
# If SUBS ends with .srt — convert to .ass first
if [[ "$SUBS" == *.srt ]]; then
  ASS="${SUBS%.srt}.ass"
  python3 "$(dirname "$0")/srt-to-ass.py" --input "$SUBS" --output "$ASS"
  SUBS="$ASS"
fi

ffmpeg -y -i "$INPUT" \
  -vf "ass=${SUBS}" \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:v libx264 -preset fast -crf 20 \
  -c:a aac -b:a 192k \
  "$OUTPUT"

echo "✅ $OUTPUT"
ls -lh "$OUTPUT"
