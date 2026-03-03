#!/bin/bash
# PreToolUse (Edit/Write): блокирует запись в clients/*/ если CLAUDE.md клиента не прочитан
# Проверяет наличие прочтения через env-переменные Claude Code
# Инциденты: 2026-02-28 (29 страниц в неправильном шаблоне), 2026-02-18 (Bootstrap вместо faq-item)

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Только файлы в clients/
if ! echo "$FILE_PATH" | grep -q "/clients/"; then
  exit 0
fi

# Определяем имя клиента
CLIENT_NAME=$(echo "$FILE_PATH" | sed 's|.*/clients/\([^/]*\)/.*|\1|')
if [ -z "$CLIENT_NAME" ]; then
  exit 0
fi

ARTVISION_DIR="/Users/antonk/artvision-data"
CLIENT_CLAUDE="$ARTVISION_DIR/clients/$CLIENT_NAME/CLAUDE.md"
CLIENT_CONFIG="$ARTVISION_DIR/clients/$CLIENT_NAME/config.yaml"

# Проверяем что CLAUDE.md клиента существует
if [ ! -f "$CLIENT_CLAUDE" ] && [ ! -f "$CLIENT_CONFIG" ]; then
  # Нет ни CLAUDE.md ни config.yaml — новый клиент, пропускаем
  exit 0
fi

# Предупреждение — НЕ блокировка (exit 0), но сообщение видно Claude
WARNINGS=""

if [ -f "$CLIENT_CLAUDE" ]; then
  WARNINGS="⚠️ PRE-TASK PROTOCOL: Перед записью в clients/$CLIENT_NAME/ — убедись что прочитал:\n"
  WARNINGS+="  1. clients/$CLIENT_NAME/CLAUDE.md\n"
fi

if [ -f "$CLIENT_CONFIG" ]; then
  WARNINGS+="  2. clients/$CLIENT_NAME/config.yaml\n"
fi

# Проверяем наличие патчей
PATCHES_DIR="$ARTVISION_DIR/clients/$CLIENT_NAME/patches"
if [ -d "$PATCHES_DIR" ] && [ "$(ls -A "$PATCHES_DIR" 2>/dev/null)" ]; then
  PATCH_COUNT=$(ls "$PATCHES_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
  WARNINGS+="  3. $PATCH_COUNT патч(ей) в clients/$CLIENT_NAME/patches/\n"
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS"
fi

exit 0
