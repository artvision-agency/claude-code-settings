#!/bin/bash
set -euo pipefail

# PreToolUse(Edit/Write) — блокирует работу с клиентскими файлами
# если не прочитаны CLAUDE.md / context-log.md / patches/

FILE_PATH="${TOOL_INPUT_FILE_PATH:-${TOOL_INPUT_PATH:-}}"
[ -z "$FILE_PATH" ] && exit 0

# Только для clients/ и projects/
echo "$FILE_PATH" | grep -qE '(clients/|projects/)' || exit 0

# Извлечь имя клиента/проекта
CLIENT=""
if echo "$FILE_PATH" | grep -q 'clients/'; then
  CLIENT=$(echo "$FILE_PATH" | sed -E 's|.*(clients/[^/]+).*|\1|')
elif echo "$FILE_PATH" | grep -q 'projects/'; then
  CLIENT=$(echo "$FILE_PATH" | sed -E 's|.*(projects/[^/]+).*|\1|')
fi
[ -z "$CLIENT" ] && exit 0

# Файл-маркер текущей сессии (создаётся после прочтения context)
MARKER="/tmp/claude-client-context-$(echo "$CLIENT" | tr '/' '-')"

if [ ! -f "$MARKER" ]; then
  # Проверяем какие файлы существуют для этого клиента
  BASE_DIR=""
  for d in "/Users/antonk/artvision-data/$CLIENT" "/Users/antonk/$CLIENT"; do
    [ -d "$d" ] && BASE_DIR="$d" && break
  done

  MISSING=""
  if [ -n "$BASE_DIR" ]; then
    [ -f "$BASE_DIR/CLAUDE.md" ] && MISSING="${MISSING}CLAUDE.md "
    [ -f "$BASE_DIR/context-log.md" ] && MISSING="${MISSING}context-log.md "
    [ -d "$BASE_DIR/patches" ] && MISSING="${MISSING}patches/ "
  fi

  if [ -n "$MISSING" ]; then
    echo "⛔ PRE-TASK PROTOCOL: Перед работой с $CLIENT прочитай: $MISSING"
    echo "После прочтения выполни: touch $MARKER"
    # Не блокируем (exit 0), но предупреждаем
  fi
fi
