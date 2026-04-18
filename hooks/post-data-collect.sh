#!/bin/bash
# PostToolUse (Write/Edit): напоминание о фактчекинге при записи данных клиентов
# Триггер: запись в clients/*, output/*, presales/* файлов с данными

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Проверяем только файлы с данными в ключевых директориях
case "$FILE_PATH" in
  */clients/*/competitors*|*/clients/*/semrush*|*/clients/*/dashboard*|*/output/company-data/*|*/presales/*|*/clients/*/kp/*|*/clients/*/presale/*)
    ;;
  *)
    exit 0
    ;;
esac

EXT="${FILE_PATH##*.}"
# Только md, html, json файлы
case "$EXT" in
  md|html|json)
    ;;
  *)
    exit 0
    ;;
esac

# Проверяем наличие числовых данных (выручка, млн, тыс, рейтинг, SKU)
HAS_DATA=$(grep -ciE '(млн|тыс|млрд|выручка|revenue|рейтинг|rating|SKU|sku|сотрудник|employee|ИНН|ОГРН|визит|visit|трафик|traffic)' "$FILE_PATH" 2>/dev/null || echo "0")
HAS_DATA=$(echo "$HAS_DATA" | tr -d '[:space:]')

if [ "$HAS_DATA" -gt 0 ]; then
  # Проверяем есть ли маркировка источника
  HAS_SOURCE=$(grep -ciE '(источник|source|дата сбора|данные:|rusprofile|checko|ozon\.ru|wildberries|similarweb|фактчек|factcheck|confirmed|подтверждено)' "$FILE_PATH" 2>/dev/null || echo "0")
  HAS_SOURCE=$(echo "$HAS_SOURCE" | tr -d '[:space:]')

  if [ "$HAS_SOURCE" -eq 0 ]; then
    echo "⚠️ FACTCHECK: $(basename "$FILE_PATH") содержит $HAS_DATA числовых утверждений БЕЗ указания источника."
    echo "→ Добавь дату сбора + источник. Проверь данные перед деплоем (см. .claude/rules/factcheck.md)"
  fi
fi

exit 0
