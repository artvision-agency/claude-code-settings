#!/bin/bash
# Stop hook: проверяет clients/*/assets/external-urls-pending.md за текущую сессию.
# Если есть pending entries без коммита в external-urls.yaml → инжектит warning.
# См. ~/.claude/rules/asset-capture-no-loss.md (Слой 4)

set -euo pipefail

# Читаем stdin (можем извлечь session_id)
INPUT=$(cat 2>/dev/null || echo "{}")
SESSION_ID=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('session_id','unknown'))" 2>/dev/null || echo "unknown")

# Ищем все pending файлы за эту сессию
CLIENTS_DIR="/Users/antonk/artvision-data/clients"
[ ! -d "$CLIENTS_DIR" ] && exit 0

PENDING_FILES=$(find "$CLIENTS_DIR"/*/assets/external-urls-pending.md 2>/dev/null || true)
[ -z "$PENDING_FILES" ] && exit 0

WARNINGS=""
for f in $PENDING_FILES; do
  # Pending entries за эту сессию
  SESSION_ENTRIES=$(grep -c "session=$SESSION_ID" "$f" 2>/dev/null || echo "0")
  [ "$SESSION_ENTRIES" -eq 0 ] && continue

  # Slug клиента
  SLUG=$(echo "$f" | sed -E 's|.*/clients/([^/]+)/.*|\1|')

  # Проверяем — был ли Edit/Write в external-urls.yaml ИЛИ access.md ИЛИ config.yaml за эту сессию
  URLS_FILE="${CLIENTS_DIR}/${SLUG}/assets/external-urls.yaml"
  ACCESS_FILE="${CLIENTS_DIR}/${SLUG}/access.md"
  CONFIG_FILE="${CLIENTS_DIR}/${SLUG}/config.yaml"

  # Считаем mtime файлов — если позже первого pending entry → значит был Write
  # Простая эвристика: если pending entry свежее last_modified ассет-файлов → не сохранено
  PENDING_MTIME=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)

  ANY_SAVED=0
  for af in "$URLS_FILE" "$ACCESS_FILE" "$CONFIG_FILE"; do
    if [ -f "$af" ]; then
      AF_MTIME=$(stat -f %m "$af" 2>/dev/null || stat -c %Y "$af" 2>/dev/null || echo 0)
      if [ "$AF_MTIME" -ge "$PENDING_MTIME" ]; then
        ANY_SAVED=1
        break
      fi
    fi
  done

  if [ "$ANY_SAVED" -eq 0 ]; then
    WARNINGS="${WARNINGS}\n  • ${SLUG}: ${SESSION_ENTRIES} pending URL/доступ не сохранён в git (см. ${f})"
  fi
done

if [ -n "$WARNINGS" ]; then
  cat >&2 <<EOF

🚧 [ASSET-CAPTURE STOP-CHECK] Сессия закрывается, но есть pending активы клиентов:
$(printf "$WARNINGS")

ПЕРЕД закрытием — Write в clients/<slug>/assets/external-urls.yaml (или access.md / config.yaml).
Правило: ~/.claude/rules/asset-capture-no-loss.md

EOF
fi

exit 0
