#!/bin/bash
# PostToolUse (Edit/Write): проверка качества кода после редактирования
# Ловит console.log, debugger, внешние URL в HTML, TODO без issue

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"
BASENAME=$(basename "$FILE_PATH")
WARNINGS=""

# === JS/TS файлы ===
if [[ "$EXT" =~ ^(js|ts|jsx|tsx|mjs|cjs)$ ]]; then
  # console.log detection
  CONSOLE_COUNT=$(grep -c "console\.\(log\|debug\|warn\|error\)" "$FILE_PATH" 2>/dev/null || echo "0")
  CONSOLE_COUNT=$(echo "$CONSOLE_COUNT" | tr -d '[:space:]')
  if [ "$CONSOLE_COUNT" -gt 0 ]; then
    LINES=$(grep -n "console\.\(log\|debug\|warn\|error\)" "$FILE_PATH" | head -5)
    WARNINGS="${WARNINGS}[lint] $BASENAME: найдено $CONSOLE_COUNT console.log/debug/warn/error:\n${LINES}\n\n"
  fi

  # debugger statements
  DEBUGGER_COUNT=$(grep -c "debugger" "$FILE_PATH" 2>/dev/null || echo "0")
  DEBUGGER_COUNT=$(echo "$DEBUGGER_COUNT" | tr -d '[:space:]')
  if [ "$DEBUGGER_COUNT" -gt 0 ]; then
    WARNINGS="${WARNINGS}[lint] $BASENAME: найден debugger statement! Удалите перед коммитом.\n\n"
  fi
fi

# === HTML файлы ===
if [[ "$EXT" == "html" ]]; then
  # Внешние URL (CDN, Google Fonts, etc)
  EXTERNAL_URLS=$(grep -oE 'https?://[^"'\''> ]+' "$FILE_PATH" 2>/dev/null | grep -v 'habr.com\|artvision\|mailto:\|tel:' | head -5)
  if [ -n "$EXTERNAL_URLS" ]; then
    URL_COUNT=$(echo "$EXTERNAL_URLS" | wc -l | tr -d ' ')
    WARNINGS="${WARNINGS}[html] $BASENAME: найдено $URL_COUNT внешних URL (запрещены для клиентских файлов):\n${EXTERNAL_URLS}\n\n"
  fi

  # Tailwind CDN
  if grep -q "cdn.tailwindcss.com\|unpkg.com/tailwind\|cdnjs.*tailwind" "$FILE_PATH" 2>/dev/null; then
    WARNINGS="${WARNINGS}[html] $BASENAME: TAILWIND CDN! Не работает на iOS Safari. Используйте inline CSS.\n\n"
  fi

  # Missing viewport
  if ! grep -qi "viewport" "$FILE_PATH" 2>/dev/null; then
    WARNINGS="${WARNINGS}[html] $BASENAME: отсутствует meta viewport — страница не будет адаптивной на мобильных.\n\n"
  fi

  # Missing lang attribute
  if ! grep -qi '<html.*lang=' "$FILE_PATH" 2>/dev/null; then
    WARNINGS="${WARNINGS}[html] $BASENAME: отсутствует lang= в <html> — проблемы с SEO и доступностью.\n\n"
  fi
fi

# === CSS файлы ===
if [[ "$EXT" == "css" ]]; then
  # @import from external
  IMPORTS=$(grep -n "@import.*http" "$FILE_PATH" 2>/dev/null | head -3)
  if [ -n "$IMPORTS" ]; then
    WARNINGS="${WARNINGS}[css] $BASENAME: внешние @import найдены:\n${IMPORTS}\n\n"
  fi
fi

# === Вывод ===
if [ -n "$WARNINGS" ]; then
  echo "---"
  echo -e "$WARNINGS"
  echo "---"
fi

exit 0
