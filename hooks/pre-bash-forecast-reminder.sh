#!/usr/bin/env bash
# pre-bash-forecast-reminder.sh — PreToolUse(Bash)
#
# Гарантия против повтора урока self-corrections #32 (2026-06-20):
#   «Forecast мёртв → нет метода для CPC» — ошибочно объявил стену, хотя
#   keywordbids.get/AuctionBids ВСЕГДА жив. Антон: «сделай чтобы всегда помнил».
#
# Ловит момент вызова МЁРТВОГО Yandex Direct Forecast API (v4 CreateNewForecast/
# GetForecast → error 509) и блокирует, тыкая в живой AuctionBids.
# Guard: срабатывает только если команда похожа на API-вызов (yandex/direct/token),
#   а не на `grep forecast` по файлу.
#
# Bypass: FORECAST_OK=1
set -uo pipefail

[[ "${FORECAST_OK:-0}" == "1" ]] && exit 0

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[[ "$TOOL" != "Bash" ]] && exit 0
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0

# Guard: пропустить команды, которые лишь УПОМИНАЮТ метод (git/grep/текст-вывод),
# а не ВЫЗЫВАЮТ API. Триггерим только реальный вызов (python/curl/node/...).
FIRST=$(printf '%s' "$CMD" | sed -e 's/^[[:space:]]*//' | awk '{print $1}')
case "$FIRST" in
  git|grep|egrep|rg|ag|cat|less|more|head|tail|sed|awk|echo|printf|ls|find|wc|diff) exit 0;;
esac

# Триггер: мёртвый Forecast-метод И признак API-вызова (не grep по файлу)
if echo "$CMD" | grep -qE 'CreateNewForecast|GetForecastList|GetForecast' \
   && echo "$CMD" | grep -qiE 'yandex|direct\.yandex|api\.direct|"token"|bearer|keywordbids'; then
  cat >&2 <<'EOF'
⛔ Forecast API Я.Директа МЁРТВ (v4 CreateNewForecast/GetForecast → error 509 «метод недоступен»).

CPC берём ТОЛЬКО через живой аукцион:
  keywordbids.get + SearchFieldNames:["AuctionBids"]  (ВСЕГДА жив, точнее всего)
  • ключи УЖЕ в кабинете → AuctionBids напрямую
  • новые ключи → залить в DRAFT-группу → AuctionBids → читать (заливка=CONFIRM)

Урок self-corrections #32 / knowledge/services/yandex-direct/gotchas.md.
Если правда нужен Forecast (напр. историч.проверка) — bypass: FORECAST_OK=1
EOF
  exit 2
fi
exit 0
