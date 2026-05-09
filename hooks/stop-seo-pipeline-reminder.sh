#!/usr/bin/env bash
# stop-seo-pipeline-reminder.sh — gentle reminder о незакрытых SEO-шагах.
#
# При Stop event сканирует filesystem (НЕ state-файл) и сравнивает с
# 8 ожидаемыми артефактами SEO-pipeline. Печатает missing в stderr.
#
# КРИТИЧНО (C2 senior review): exit 0 ВСЕГДА. Stop-hook с exit != 0 ломает session loop.
# Только context injection через stderr.
#
# Триггер: sentinel /tmp/seo-master-invoked-${session_id} существует
# (значит Skill seo-master был вызван в этой сессии).
#
# Логика:
# 1. Sentinel есть → seo-master сессия → продолжаем
# 2. Sentinel нет → не SEO-сессия → exit 0 silently
# 3. Получаем mtime sentinel = когда seo-master был вызван
# 4. Сканируем ~/artvision-data/clients/*/seo/ файлы с mtime > sentinel
# 5. Считаем сколько из 8 категорий артефактов покрыто
# 6. Если <8 — печатаем missing в stderr
#
# Защита от спама: stop_hook_active=true в input → один раз в Stop-loop, не зацикливаемся.

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

SESSION_ID=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", ""))
except Exception:
    print("")
' 2>/dev/null || echo "")

[ -z "$SESSION_ID" ] && exit 0

SENTINEL="/tmp/seo-master-invoked-$SESSION_ID"
[ ! -f "$SENTINEL" ] && exit 0  # не SEO-сессия

# Anti-loop: если уже напомнили в этом Stop-event цикле
LOOP_MARKER="/tmp/seo-stop-reminded-$SESSION_ID"
if [ -f "$LOOP_MARKER" ]; then
  # Если marker свежее 60 сек — пропускаем (уже напоминали)
  AGE=$(( $(date +%s) - $(stat -f %m "$LOOP_MARKER" 2>/dev/null || echo 0) ))
  [ "$AGE" -lt 60 ] && exit 0
fi

CLIENTS_DIR="$HOME/artvision-data/clients"
[ ! -d "$CLIENTS_DIR" ] && exit 0

SENTINEL_TS=$(stat -f %m "$SENTINEL" 2>/dev/null || echo 0)
[ "$SENTINEL_TS" -eq 0 ] && exit 0

# 8 ожидаемых категорий артефактов
# Plain vars (macOS bash 3.2 не имеет associative arrays)
F_SF=0
F_LH_M=0
F_LH_D=0
F_WS=0
F_TV=0
F_COMP=0
F_FC=0
F_RPT=0

TMP_MARKER=$(mktemp -t seo-sentinel-marker)
trap 'rm -f "$TMP_MARKER"' EXIT
touch -t "$(date -r "$SENTINEL_TS" '+%Y%m%d%H%M.%S')" "$TMP_MARKER" 2>/dev/null || touch "$TMP_MARKER"

while IFS= read -r f; do
  case "$f" in
    *sf-out/internal_html.csv|*sf-*.csv)        F_SF=1 ;;
    *lhr-*mobile*.json|*lighthouse-*/mobile*.json|*lighthouse-mobile*.json) F_LH_M=1 ;;
    *lhr-*desktop*.json|*lighthouse-*/desktop*.json|*lighthouse-desktop*.json) F_LH_D=1 ;;
    *wordstat-*.csv)                            F_WS=1 ;;
    *topvisor-*.json|*positions-*.json|*positions-*.csv) F_TV=1 ;;
    *competitors-*.md|*competitors-*.csv|*competitors-*.json) F_COMP=1 ;;
    *factcheck-*.md|*factcheck-report-*.json|*factcheck-*.json) F_FC=1 ;;
    */kp/*.html|*audit-*.html|*audit_*.html)    F_RPT=1 ;;
  esac
done < <(find "$CLIENTS_DIR"/*/seo "$CLIENTS_DIR"/*/kp -type f -newer "$TMP_MARKER" 2>/dev/null | head -100)

COVERED=$((F_SF + F_LH_M + F_LH_D + F_WS + F_TV + F_COMP + F_FC + F_RPT))
TOTAL=8
MISSING_LIST=""
[ "$F_SF" -eq 0 ]    && MISSING_LIST="$MISSING_LIST screaming_frog"
[ "$F_LH_M" -eq 0 ]  && MISSING_LIST="$MISSING_LIST lighthouse_mobile"
[ "$F_LH_D" -eq 0 ]  && MISSING_LIST="$MISSING_LIST lighthouse_desktop"
[ "$F_WS" -eq 0 ]    && MISSING_LIST="$MISSING_LIST wordstat_freq"
[ "$F_TV" -eq 0 ]    && MISSING_LIST="$MISSING_LIST topvisor_positions"
[ "$F_COMP" -eq 0 ]  && MISSING_LIST="$MISSING_LIST competitor_audit"
[ "$F_FC" -eq 0 ]    && MISSING_LIST="$MISSING_LIST factcheck"
[ "$F_RPT" -eq 0 ]   && MISSING_LIST="$MISSING_LIST report_html"

# Все 8 покрыты → silent
[ "$COVERED" -eq "$TOTAL" ] && exit 0

# 0 покрыто → значит seo-master был вызван но артефактов не появилось
# Это OK — может пользователь только начал. Не спамим.
[ "$COVERED" -eq 0 ] && exit 0

# Где-то посередине — gentle reminder
{
  echo ""
  echo "📋 SEO Pipeline reminder ($COVERED/$TOTAL шагов покрыто):"
  for step in $MISSING_LIST; do
    case "$step" in
      screaming_frog)      echo "  ⏳ Screaming Frog crawl — sf <url> --output-folder clients/<name>/seo/<date>/sf-out/" ;;
      lighthouse_mobile)   echo "  ⏳ Lighthouse mobile — lhci collect --url=<url> --settings.preset=mobile" ;;
      lighthouse_desktop)  echo "  ⏳ Lighthouse desktop — lhci collect --url=<url> --settings.preset=desktop" ;;
      wordstat_freq)       echo "  ⏳ Wordstat частоты — scripts/yandex/wordstat_or_fallback.py" ;;
      topvisor_positions)  echo "  ⏳ Позиции Topvisor — get/positions_2/history" ;;
      competitor_audit)    echo "  ⏳ Конкуренты — competitors-*.md в clients/<name>/seo/" ;;
      factcheck)           echo "  ⏳ Factcheck — factcheck-v2.py перед деплоем" ;;
      report_html)         echo "  ⏳ HTML отчёт — clients/<name>/kp/*.html" ;;
    esac
  done
  echo ""
  echo "(reminder, не блок — продолжай если эти шаги намеренно пропущены)"
} >&2

# Помечаем что напомнили в этом цикле
touch "$LOOP_MARKER" 2>/dev/null || true

exit 0
