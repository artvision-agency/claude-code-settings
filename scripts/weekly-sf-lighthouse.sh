#!/usr/bin/env bash
# weekly-sf-lighthouse.sh — еженедельный фон-краул SF+Lighthouse по всем активным клиентам Artvision.
#
# Запуск: вручную `~/.claude/scripts/weekly-sf-lighthouse.sh` или через LaunchAgent
#         pro.artvision.weekly-sf-lighthouse (раз в неделю в 03:00 ночи).
#
# Логика:
# 1. Сканирует ~/artvision-data/clients/*/config.yaml — извлекает URL клиента
# 2. Для каждого активного клиента (есть config.yaml + не "stop"-flag):
#    - SF crawl → clients/<name>/seo/sf-out-<date>/
#    - Lighthouse mobile+desktop → clients/<name>/seo/lighthouse-<date>/
# 3. Лог: ~/.claude/logs/weekly-sf-lighthouse-<date>.log
# 4. По завершении: TG-нотификация в team-чат с сводкой (если tg-send.sh доступен)
#
# Ограничения:
# - Параллелизм: 1 (последовательно — SF и Lighthouse тяжёлые на процессор)
# - Timeout per-client: 10 мин
# - Skip если есть свежий артефакт <3 дня (избегаем дублей при ручном запуске)
#
set -euo pipefail

CLIENTS_DIR="$HOME/artvision-data/clients"
LOG_DIR="$HOME/.claude/logs"
DATE=$(date +%Y-%m-%d)
LOG="$LOG_DIR/weekly-sf-lighthouse-$DATE.log"
SUMMARY="$LOG_DIR/weekly-sf-lighthouse-$DATE.summary.txt"
SF_BIN="/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher"
LHCI_BIN="$HOME/.local/npm-global/bin/lhci"
mkdir -p "$LOG_DIR"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }
log "=== weekly-sf-lighthouse start ==="

DONE=0; SKIPPED=0; FAILED=0
: > "$SUMMARY"

for client_yaml in "$CLIENTS_DIR"/*/config.yaml; do
  [[ -f "$client_yaml" ]] || continue
  client_dir=$(dirname "$client_yaml")
  client_name=$(basename "$client_dir")

  # Skip system / non-client folders
  case "$client_name" in
    _template|_*|.*|example|test|sample|tmp)
      log "SKIP $client_name (system folder)"
      SKIPPED=$((SKIPPED+1))
      continue
      ;;
  esac

  # Skip stop-clients (если в config есть stop:true или папка stopped/)
  if grep -qE '^(stopped|paused|stop):\s*true' "$client_yaml" 2>/dev/null; then
    log "SKIP $client_name (stopped)"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  url=$(grep -oE 'https?://[^"[:space:]]+' "$client_yaml" 2>/dev/null | head -1 || true)
  if [[ -z "$url" ]]; then
    log "SKIP $client_name (no URL in config)"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  # Skip placeholder/test URLs and non-crawlable platforms
  case "$url" in
    *example.com*|*example.org*|*localhost*|*127.0.0.1*|*test.local*)
      log "SKIP $client_name (placeholder URL: $url)"
      SKIPPED=$((SKIPPED+1))
      continue
      ;;
    *vk.com/*|*wa.me/*|*t.me/*|*instagram.com/*|*facebook.com/*|*ozon.ru/seller/*|*wildberries.ru/seller/*)
      log "SKIP $client_name (social/marketplace URL, not crawlable: $url)"
      SKIPPED=$((SKIPPED+1))
      continue
      ;;
  esac

  # Skip if already fresh (<3 days)
  fresh_sf=$(find "$client_dir/seo" -name "*.csv" -mtime -3 2>/dev/null | head -1)
  fresh_lh=$(find "$client_dir/seo" -name "lhr-*.json" -mtime -3 2>/dev/null | head -1)
  if [[ -n "$fresh_sf" && -n "$fresh_lh" ]]; then
    log "SKIP $client_name (artifacts fresh < 3d)"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  log "RUN $client_name url=$url"
  client_seo="$client_dir/seo/$DATE"
  mkdir -p "$client_seo"

  # SF crawl (timeout 10min)
  if timeout 600 "$SF_BIN" \
      --crawl "$url" --headless --save-crawl \
      --output-folder "$client_seo" \
      --export-format csv \
      --export-tabs "Internal:All,Response Codes:Client Error (4xx),Response Codes:Server Error (5xx),Response Codes:Redirection (3xx),Page Titles:Missing,Page Titles:Duplicate,Meta Description:Missing,H1:Missing,Canonicals:Missing" \
      --overwrite >>"$LOG" 2>&1; then
    sf_csv=$(ls "$client_seo"/*.csv 2>/dev/null | wc -l | tr -d ' ')
    log "  SF ok: $sf_csv CSV"
  else
    log "  SF FAIL exit=$?"
    FAILED=$((FAILED+1))
    echo "$client_name SF_FAIL" >> "$SUMMARY"
    continue
  fi

  # Lighthouse mobile (cd into client_seo because lhci writes .lighthouseci/ in cwd)
  if [[ -x "$LHCI_BIN" ]]; then
    mkdir -p "$client_seo/lighthouse"
    if (cd "$client_seo/lighthouse" && timeout 300 "$LHCI_BIN" collect \
        --url="$url" \
        --numberOfRuns=1 \
        --settings.chromeFlags="--headless --no-sandbox --disable-gpu" >>"$LOG" 2>&1); then
      # Move lhr files to absolute output dir (lhci writes to ./lighthouseci/ relative)
      mv "$client_seo/lighthouse/.lighthouseci/"* "$client_seo/lighthouse/" 2>/dev/null
      rmdir "$client_seo/lighthouse/.lighthouseci" 2>/dev/null
      log "  Lighthouse ok"
    else
      log "  Lighthouse FAIL exit=$?"
      FAILED=$((FAILED+1))
      echo "$client_name LIGHTHOUSE_FAIL" >> "$SUMMARY"
      continue
    fi
  else
    log "  Lighthouse SKIP (lhci not at $LHCI_BIN)"
  fi

  DONE=$((DONE+1))
  echo "$client_name OK $client_seo" >> "$SUMMARY"
done

log "=== done: $DONE ok, $SKIPPED skipped, $FAILED failed ==="
log "Summary: $SUMMARY"

# Optional TG notification
TG_SCRIPT="$HOME/.claude/scripts/tg-send.sh"
if [[ -x "$TG_SCRIPT" ]]; then
  msg="📊 Weekly SF+Lighthouse · $DATE
✅ ok: $DONE · ⏸ skip: $SKIPPED · ❌ fail: $FAILED
Лог: $LOG"
  "$TG_SCRIPT" team "$msg" >>"$LOG" 2>&1 || log "TG notify failed (ignored)"
fi
