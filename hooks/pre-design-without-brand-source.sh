#!/usr/bin/env bash
# pre-design-without-brand-source.sh — PreToolUse(Edit|Write) для design-задач клиента
#
# Блокирует Edit/Write дизайнерских артефактов (HTML/PNG/SVG/JPG в дизайн-папках клиента)
# пока не выполнено извлечение фирстиля через /brand-extraction (свежее, < 7 дней).
#
# ПРЕЦЕДЕНТ: USmile 27.05.2026 — 4 часа на бирюзовых макетах при настоящем красно-белом
# бренде. Корень — не извлекли sprite сайта клиента до начала дизайна.
# Источник lesson: clients/usmile/LESSONS-2026-05-27.md
#
# Bypass:
#   BRAND_SOURCE_OK=1 — явное согласие что бренд проверен
#   /tmp/brand-source-done-{SESSION_ID} — snooze на сессию

set -uo pipefail

# 1) Bypass через env
if [[ "${BRAND_SOURCE_OK:-0}" == "1" ]]; then
  echo "[brand-source] BYPASS via BRAND_SOURCE_OK=1" >&2
  exit 0
fi

# 2) Read stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

# 3) Только Edit/Write/MultiEdit — остальное пропускаем
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) :;;
  *) exit 0;;
esac

# 4) Snooze для сессии
[[ -n "$SESSION_ID" && -f "/tmp/brand-source-done-${SESSION_ID}" ]] && exit 0

# 5) Извлекаем file_path
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE_PATH" ]] && exit 0

# 6) Match только design-paths внутри clients/<slug>/
#    Триггер: HTML/PNG/SVG/JPG в:
#      clients/*/ideas/*
#      clients/*/presale/kp/*
#      clients/*/presale/*/kp/*
#      clients/*/landings/*
#      clients/*/signage/*
#      clients/*/pages/*
#      clients/*/mockups/*
#    Игнор: assets/, logo-real/, _archive/, _REJECTED/, backups/
if ! echo "$FILE_PATH" | grep -qE 'clients/[^/]+/(ideas|presale|landings|signage|pages|mockups)(/|$)'; then
  exit 0
fi
# исключаем папки с готовыми ассетами / архивы
if echo "$FILE_PATH" | grep -qE '/(assets|logo-real|_archive|_REJECTED|backups|node_modules)/'; then
  exit 0
fi
# исключаем расширения не-дизайн
case "${FILE_PATH##*.}" in
  html|png|svg|jpg|jpeg|webp|ai|psd|pdf) :;;
  *) exit 0;;
esac

# 7) Достаём client slug
CLIENT_SLUG=$(echo "$FILE_PATH" | sed -E 's|.*/clients/([^/]+)/.*|\1|')
[[ -z "$CLIENT_SLUG" || "$CLIENT_SLUG" == "$FILE_PATH" ]] && exit 0

# 8) Ищем artvision-data корень из file_path
ARTVISION_ROOT=$(echo "$FILE_PATH" | sed -E 's|(.*/artvision-data)/clients/.*|\1|')
[[ -z "$ARTVISION_ROOT" || ! -d "$ARTVISION_ROOT" ]] && ARTVISION_ROOT="$HOME/artvision-data"

CLIENT_DIR="$ARTVISION_ROOT/clients/$CLIENT_SLUG"
BRAND_MANIFEST="$CLIENT_DIR/assets/logo-real/brand-extracted.yaml"
ELEMENTS_DIR="$CLIENT_DIR/assets/logo-real/elements"

# 9) Проверка наличия brand-extracted.yaml
if [[ ! -f "$BRAND_MANIFEST" ]]; then
  cat >&2 <<EOF

⛔ BLOCKED: дизайн-задача для клиента "$CLIENT_SLUG" без извлечённого фирстиля.

   Файл: $FILE_PATH
   Не найден: $BRAND_MANIFEST

   ПРЕЦЕДЕНТ: USmile 27.05.2026 — 4 часа на бирюзовых макетах вместо красно-белых,
   потому что не извлекли бренд из sprite сайта клиента до начала дизайна.

   ДЕЙСТВИЕ:
   1. Вызови Skill brand-extraction:
        /brand-extraction $CLIENT_SLUG
      ИЛИ запусти руками:
        python3 ~/.claude/skills/brand-extraction/scripts/extract_brand.py \\
            --slug $CLIENT_SLUG \\
            --url <site-url> \\
            --output $CLIENT_DIR/assets/logo-real/

   2. Проверь brand-extracted.yaml: цвета, шрифты, элементы.
   3. Используй настоящие ассеты из assets/logo-real/elements/ в дизайне.

   Bypass (только если знаешь зачем):
     BRAND_SOURCE_OK=1 <команда>
   Или snooze на сессию:
     touch /tmp/brand-source-done-${SESSION_ID}

   Связано:
     - ~/.claude/skills/brand-extraction/SKILL.md
     - clients/$CLIENT_SLUG/LESSONS-*.md (если есть)
     - ~/.claude/rules/quality.md (Pre-Task Protocol)

EOF
  exit 2
fi

# 10) Проверка свежести (< 7 дней)
if [[ "$(uname)" == "Darwin" ]]; then
  MANIFEST_AGE_DAYS=$(( ($(date +%s) - $(stat -f %m "$BRAND_MANIFEST")) / 86400 ))
else
  MANIFEST_AGE_DAYS=$(( ($(date +%s) - $(stat -c %Y "$BRAND_MANIFEST")) / 86400 ))
fi

if (( MANIFEST_AGE_DAYS > 7 )); then
  cat >&2 <<EOF

⚠️  WARNING: brand-extracted.yaml для "$CLIENT_SLUG" устарел ($MANIFEST_AGE_DAYS дней).

   Файл: $BRAND_MANIFEST
   Сайт клиента мог обновить дизайн с момента извлечения.

   РЕКОМЕНДАЦИЯ: перезапустить /brand-extraction $CLIENT_SLUG

   Чтобы продолжить с устаревшим:
     BRAND_SOURCE_OK=1 <команда>
   ИЛИ touch /tmp/brand-source-done-${SESSION_ID}

EOF
  exit 2
fi

# 11) Опционально — есть ли вырезанные элементы
if [[ ! -d "$ELEMENTS_DIR" ]] || [[ -z "$(ls -A "$ELEMENTS_DIR" 2>/dev/null)" ]]; then
  cat >&2 <<EOF

⚠️  WARNING: $ELEMENTS_DIR пуст или отсутствует.
   brand-extracted.yaml есть, но элементы не вырезаны — sprite клиента может не существовать.
   Это нормально для клиентов без sprite, но проверь.

EOF
  # не блокируем — warning only
fi

# Всё ок
exit 0
