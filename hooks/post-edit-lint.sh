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

# === Проверка регрессии: удалено >20% строк (в clients/) ===
if echo "$FILE_PATH" | grep -q "/clients/"; then
  if command -v git >/dev/null 2>&1; then
    REPO_DIR=$(cd "$(dirname "$FILE_PATH")" && git rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$REPO_DIR" ]; then
      REL_PATH="${FILE_PATH#$REPO_DIR/}"
      DIFF_STAT=$(cd "$REPO_DIR" && git diff --numstat -- "$REL_PATH" 2>/dev/null)
      if [ -n "$DIFF_STAT" ]; then
        ADDED=$(echo "$DIFF_STAT" | awk '{print $1}')
        DELETED=$(echo "$DIFF_STAT" | awk '{print $2}')
        if [ "$DELETED" -gt 0 ] 2>/dev/null && [ "$ADDED" -lt "$DELETED" ] 2>/dev/null; then
          NET_LOSS=$((DELETED - ADDED))
          ORIG_LINES=$(cd "$REPO_DIR" && git show HEAD:"$REL_PATH" 2>/dev/null | wc -l | tr -d ' ')
          if [ "$ORIG_LINES" -gt 0 ] 2>/dev/null; then
            PCT=$((NET_LOSS * 100 / ORIG_LINES))
            if [ "$PCT" -gt 20 ]; then
              WARNINGS="${WARNINGS}[regression] $BASENAME: УДАЛЕНО ${PCT}% контента (${NET_LOSS} строк из ${ORIG_LINES})!\n[regression] Это может быть регрессия. Проверь git diff.\n\n"
            fi
          fi
        fi
      fi
    fi
  fi
fi

# === Вывод ===
if [ -n "$WARNINGS" ]; then
  echo "---"
  echo -e "$WARNINGS"
  echo "---"
fi

exit 0
