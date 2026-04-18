#!/bin/bash
set -euo pipefail

# Post-hook: при Edit/Write файлов в clients/* — добавляет запись в context-log.md клиента
# Событие: PostToolUse (Edit, Write)
# Цель: единый лог решений по каждому клиенту, переживающий все сессии
# Вызов: post-client-context-log.sh "$CLAUDE_FILE_PATH"

FILE_PATH="${1:-}"

# Нет пути — выходим
if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Проверяем что это файл клиента
if [[ ! "$FILE_PATH" == *"/clients/"* ]]; then
  exit 0
fi

# Не логируем сам context-log
if [[ "$FILE_PATH" == *"context-log.md" ]]; then
  exit 0
fi

# Извлекаем имя клиента
CLIENT_NAME=$(echo "$FILE_PATH" | sed -n 's|.*/clients/\([^/]*\)/.*|\1|p')
if [[ -z "$CLIENT_NAME" || "$CLIENT_NAME" == "_template" || "$CLIENT_NAME" == "_leads" ]]; then
  exit 0
fi

# Определяем базовую директорию clients
CLIENTS_BASE=$(echo "$FILE_PATH" | sed "s|/clients/$CLIENT_NAME/.*|/clients/$CLIENT_NAME|")

# Путь к context-log
CONTEXT_LOG="$CLIENTS_BASE/context-log.md"
RELATIVE_FILE=$(echo "$FILE_PATH" | sed "s|.*/clients/$CLIENT_NAME/||")
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")

# Создаём файл если не существует
if [[ ! -f "$CONTEXT_LOG" ]]; then
  cat > "$CONTEXT_LOG" << HEADER
# Context Log — $CLIENT_NAME

Единый лог действий и решений по проекту. Пополняется автоматически при каждой сессии.

---

HEADER
fi

# Проверяем — не дублируем запись за ту же минуту с тем же файлом
LAST_LINE=$(tail -1 "$CONTEXT_LOG" 2>/dev/null || echo "")
ENTRY="- **$TIMESTAMP** | \`$RELATIVE_FILE\`"
if [[ "$LAST_LINE" == "$ENTRY" ]]; then
  exit 0
fi

echo "$ENTRY" >> "$CONTEXT_LOG"
exit 0
