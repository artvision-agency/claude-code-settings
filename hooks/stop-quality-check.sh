#!/bin/bash
# Stop: проверка качества перед завершением сессии
# Ловит: незакоммиченные изменения, TODO, непротестированные скрипты

cd /Users/antonk/artvision-data 2>/dev/null || exit 0

ISSUES=""

# === Незакоммиченные изменения в клиентских файлах ===
CLIENT_CHANGES=$(git diff --name-only 2>/dev/null | grep "^clients/" | head -10)
if [ -n "$CLIENT_CHANGES" ]; then
  COUNT=$(echo "$CLIENT_CHANGES" | wc -l | tr -d ' ')
  ISSUES="${ISSUES}[stop] $COUNT незакоммиченных файлов клиентов:\n"
  ISSUES="${ISSUES}${CLIENT_CHANGES}\n\n"
fi

# === TODO/FIXME в изменённых файлах ===
MODIFIED=$(git diff --name-only 2>/dev/null | head -20)
if [ -n "$MODIFIED" ]; then
  TODO_LIST=""
  while IFS= read -r f; do
    if [ -f "$f" ]; then
      TODOS=$(grep -n "TODO\|FIXME\|HACK\|XXX" "$f" 2>/dev/null | head -3)
      if [ -n "$TODOS" ]; then
        TODO_LIST="${TODO_LIST}  $f:\n${TODOS}\n"
      fi
    fi
  done <<< "$MODIFIED"
  if [ -n "$TODO_LIST" ]; then
    ISSUES="${ISSUES}[stop] TODO/FIXME в изменённых файлах:\n${TODO_LIST}\n"
  fi
fi

# === Внешние URL в HTML клиентов (финальная проверка) ===
HTML_CHANGES=$(git diff --name-only 2>/dev/null | grep "\.html$" | head -10)
if [ -n "$HTML_CHANGES" ]; then
  while IFS= read -r f; do
    if [ -f "$f" ]; then
      EXT_URLS=$(grep -oE 'https?://[^"'\''> ]+' "$f" 2>/dev/null | grep -v 'habr.com\|artvision\|mailto:\|tel:\|#' | head -3)
      if [ -n "$EXT_URLS" ]; then
        ISSUES="${ISSUES}[stop] Внешние URL в $f:\n${EXT_URLS}\n\n"
      fi
    fi
  done <<< "$HTML_CHANGES"
fi

# === Вывод ===
if [ -n "$ISSUES" ]; then
  echo "=== Session Quality Check ==="
  echo -e "$ISSUES"
  echo "============================="
fi

exit 0
