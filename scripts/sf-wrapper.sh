#!/usr/bin/env bash
# sf — обёртка над Screaming Frog SEO Spider CLI (headless)
# Установлен как ~/.local/bin/sf (через симлинк).
#
# Зачем: Claude Code и хуки не должны помнить путь к Application bundle.
# Команда `sf <url>` запускает SF в headless-режиме, экспортирует стандартный
# набор tabs в CSV, лог пишется в ~/.claude/logs/sf-runs.log.
#
# Использование:
#   sf <url>                                    — стандартный набор экспортов в /tmp/sf-out-<hash>/
#   sf <url> --output-folder <dir>              — кастомный output
#   sf <url> --tabs "Internal:All,..."          — кастомные tabs
#   sf <url> --depth 3 --max-urls 1000          — лимиты краула
#   sf --raw -- <flags>                         — passthrough в SF CLI без обвязки
#   sf --help                                   — этот help
#
# Примеры:
#   sf https://madwave.eu --output-folder ~/artvision-data/clients/madwave/eu/sf-out
#   sf https://otido.ru --tabs "Response Codes:Client Error (4xx),Page Titles:Duplicate"
#
# Лог: ~/.claude/logs/sf-runs.log (URL, дата, output, exit code)
#
set -euo pipefail

SF_BIN="/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher"
LOG_FILE="$HOME/.claude/logs/sf-runs.log"
mkdir -p "$(dirname "$LOG_FILE")"

if [[ ! -x "$SF_BIN" ]]; then
  echo "ERROR: Screaming Frog не установлен или путь изменился: $SF_BIN" >&2
  exit 127
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || $# -eq 0 ]]; then
  sed -n '2,/^set -e/p' "$0" | sed 's/^# //;s/^#//' | head -25
  exit 0
fi

if [[ "${1:-}" == "--raw" ]]; then
  shift
  echo "[$(date -u +%FT%TZ)] sf --raw $*" >> "$LOG_FILE"
  exec "$SF_BIN" "$@"
fi

URL="$1"; shift
OUT_DIR=""
TABS="Internal:All,Response Codes:Client Error (4xx),Response Codes:Server Error (5xx),Response Codes:Redirection (3xx),Page Titles:Missing,Page Titles:Duplicate,Meta Description:Missing,H1:Missing,Canonicals:Missing"
DEPTH=""
MAX_URLS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-folder) OUT_DIR="$2"; shift 2 ;;
    --tabs) TABS="$2"; shift 2 ;;
    --depth) DEPTH="$2"; shift 2 ;;
    --max-urls) MAX_URLS="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$OUT_DIR" ]]; then
  hash=$(echo -n "$URL" | shasum | cut -c1-8)
  OUT_DIR="/tmp/sf-out-$hash-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$OUT_DIR"

CONFIG_ARGS=()
if [[ -n "$DEPTH" ]]; then CONFIG_ARGS+=(--config "depth=$DEPTH"); fi

START_TS=$(date -u +%FT%TZ)
echo "[$START_TS] sf start url=$URL out=$OUT_DIR tabs=$TABS depth=${DEPTH:-default} max=${MAX_URLS:-default}" >> "$LOG_FILE"

set +e
"$SF_BIN" \
  --crawl "$URL" \
  --headless \
  --save-crawl \
  --output-folder "$OUT_DIR" \
  --export-format csv \
  --export-tabs "$TABS" \
  --overwrite
EXIT=$?
set -e

END_TS=$(date -u +%FT%TZ)
NUM_CSV=$(ls "$OUT_DIR"/*.csv 2>/dev/null | wc -l | tr -d ' ')
echo "[$END_TS] sf end url=$URL exit=$EXIT csv_files=$NUM_CSV out=$OUT_DIR" >> "$LOG_FILE"

if [[ $EXIT -eq 0 ]]; then
  echo "✅ SF crawl complete: $OUT_DIR ($NUM_CSV CSV files)"
  ls "$OUT_DIR"/*.csv 2>/dev/null | head -10
else
  echo "❌ SF exit=$EXIT — см. $LOG_FILE"
fi
exit $EXIT
