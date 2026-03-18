#!/usr/bin/env bash
set -euo pipefail

# memory-recall.sh — обёртка для memory-search.py
# Вызывается из SessionStart хука или вручную.
# Принимает контекст из stdin или аргументом.
# Возвращает JSON с additionalContext для инъекции в промпт.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEARCH_SCRIPT="${SCRIPT_DIR}/memory-search.py"

if [[ ! -f "$SEARCH_SCRIPT" ]]; then
    echo '{"additionalContext": "Memory search script not found"}' >&2
    exit 1
fi

# Получаем query: из аргументов или stdin
if [[ $# -gt 0 ]]; then
    QUERY="$*"
elif [[ ! -t 0 ]]; then
    QUERY="$(cat)"
else
    echo "Usage: memory-recall.sh <query>" >&2
    echo "       echo 'context' | memory-recall.sh" >&2
    exit 1
fi

if [[ -z "${QUERY:-}" ]]; then
    echo '{"additionalContext": "Empty query, no memory recall"}' >&2
    exit 1
fi

# Извлекаем ключевые слова (первые 200 символов, без спецсимволов)
QUERY_CLEAN="$(echo "$QUERY" | head -c 200 | tr -d '\n\r')"

# Запускаем поиск
RESULTS="$(python3 "$SEARCH_SCRIPT" --json "$QUERY_CLEAN" 2>/dev/null || echo '[]')"

# Если результаты пустые — выходим тихо
if [[ "$RESULTS" == "[]" ]] || [[ -z "$RESULTS" ]]; then
    echo '{"additionalContext": ""}'
    exit 0
fi

# Собираем human-readable формат для additionalContext
READABLE="$(python3 "$SEARCH_SCRIPT" "$QUERY_CLEAN" 2>/dev/null || echo '')"

# Формируем JSON ответ
# Используем Python для безопасной JSON-сериализации
python3 -c "
import json, sys

readable = sys.stdin.read().strip()
if not readable:
    print(json.dumps({'additionalContext': ''}))
else:
    ctx = '## Memory Recall (auto)\n\n' + readable + '\n\nЧитай релевантные файлы при необходимости.'
    print(json.dumps({'additionalContext': ctx}, ensure_ascii=False))
" <<< "$READABLE"
