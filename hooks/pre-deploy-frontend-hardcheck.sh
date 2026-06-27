#!/usr/bin/env bash
# pre-deploy-frontend-hardcheck.sh — PreToolUse(Bash), WARN-only (НЕ блокирует деплой).
#
# Зачем: текстовый factcheck слеп к визуалу — битые/пустые картинки уходили в прод.
# Этот хук ловит момент деплоя клиентского HTML (safe-deploy-html.sh ИЛИ
# scp ... /var/www/artvision/...html) и быстро (frontend-hardcheck.py --fast)
# проверяет картинки целевого URL. Если есть битые/пустые — печатает WARNING,
# но ВСЕГДА exit 0 (деплой не блокируется — только предупреждение).
#
# Правило: ~/.claude/rules/checks-by-validators-multimodel.md (проверки несут валидаторы).
# Bypass: HARDCHECK_OK=1
set -uo pipefail

[[ "${HARDCHECK_OK:-0}" == "1" ]] && exit 0

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[[ "$TOOL" != "Bash" ]] && exit 0
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0

# Триггер: деплой клиентского HTML.
#  (a) safe-deploy-html.sh   ИЛИ
#  (b) scp ... /var/www/artvision/<...>.html(m)
IS_SAFE=0; IS_SCP=0
echo "$CMD" | grep -q 'safe-deploy-html\.sh' && IS_SAFE=1
echo "$CMD" | grep -qE 'scp\b' && echo "$CMD" | grep -qE '/var/www/artvision/[^ ]*\.html?m?\b' && IS_SCP=1
[[ "$IS_SAFE" == "0" && "$IS_SCP" == "0" ]] && exit 0

# Извлечь путь назначения /var/www/artvision/<path>[/index.html] → URL.
DEST=$(echo "$CMD" | grep -oE '/var/www/artvision/[^ "'\'']*' | head -1)
[[ -z "$DEST" ]] && exit 0
REL=${DEST#/var/www/artvision/}
REL=${REL%index.html}     # .../foo/index.html → .../foo/
REL=${REL%index.htm}
# если назначение — конкретный .html (не index), оставляем как есть
URL="https://artvision.pro/${REL}"
# нормализуем двойные слэши (кроме https://)
URL=$(echo "$URL" | sed -E 's#([^:])//+#\1/#g')

HARDCHECK="$HOME/artvision-data/scripts/ppc/frontend-hardcheck.py"
[[ ! -f "$HARDCHECK" ]] && exit 0

# Быстрая детерминированная проверка картинок (без браузера/vision).
OUT=$(timeout 30 python3 "$HARDCHECK" --fast --url "$URL" 2>&1 || true)

# Сигналы проблемных картинок (broken/empty src/empty base64).
if echo "$OUT" | grep -qE 'картинка не отдаётся|EMPTY-SRC|пустой src|EMPTY base64' \
   || echo "$OUT" | grep -qE 'битые/недоступные +[1-9]'; then
  {
    echo "⚠️  FRONTEND HARDCHECK (WARN, деплой НЕ заблокирован) — $URL"
    echo "    Обнаружены проблемные картинки перед деплоем:"
    echo "$OUT" | grep -E 'битые/недоступные|пустые base64|картинка не отдаётся|EMPTY' | sed 's/^/      /'
    echo "    Проверь полностью:  python3 $HARDCHECK --url $URL"
    echo "    Заглушить хук:      HARDCHECK_OK=1"
  } >&2
fi

exit 0
