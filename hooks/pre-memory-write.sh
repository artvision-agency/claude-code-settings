#!/bin/bash
# PreToolUse (Write): при создании нового файла в ~/.claude/projects/-Users-antonk/memory/
# ищет похожие существующие и выводит WARN если найдены.
# Не блокирует — даёт рекомендацию обновить существующий.
#
# Инцидент 2026-04-17: создание feedback_*.md вместо обновления похожих,
# 135+ файлов, dubli в _archive_pre_cleanup_20260324/.
set -euo pipefail

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"
[ -n "$FILE_PATH" ] || exit 0

MEMORY_DIR="$HOME/.claude/projects/-Users-antonk/memory"

# Триггер только на файлы в memory/
case "$FILE_PATH" in
    "$MEMORY_DIR"/*) ;;
    *) exit 0 ;;
esac

# Исключения
BASENAME=$(basename "$FILE_PATH")
case "$BASENAME" in
    MEMORY.md|README.md) exit 0 ;;
esac

# Если файл уже существует — это обновление, не создание → пропускаем
[ -f "$FILE_PATH" ] && exit 0

# Пытаемся достать новое содержимое из stdin JSON (Claude Code передаёт tool_input)
INPUT=$(cat 2>/dev/null || echo '{}')
NEW_CONTENT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('content', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# Если содержимого нет — не можем сравнить, только предупредим по имени
if [ -z "$NEW_CONTENT" ]; then
    # Поиск по похожему имени
    STEM="${BASENAME%.md}"
    # Выделяем ядро имени (после первого _)
    CORE=$(echo "$STEM" | sed 's/^[a-z]*_//')
    [ -z "$CORE" ] && exit 0
    SIMILAR=$(ls "$MEMORY_DIR"/*.md 2>/dev/null | xargs -n1 basename 2>/dev/null | grep -i "$CORE" | grep -v "^${BASENAME}\$" | head -3 || true)
    if [ -n "$SIMILAR" ]; then
        echo "⚠️  pre-memory-write: создаётся $BASENAME, похожие существуют:" >&2
        echo "$SIMILAR" | sed 's/^/    /' >&2
        echo "   → рассмотреть обновление вместо создания" >&2
    fi
    exit 0
fi

# Вызываем Python helper для fuzzy-матчинга
export MEMORY_DIR NEW_CONTENT BASENAME
python3 ~/.claude/scripts/memory-dedup-check.py 2>&1 >&2 || true

exit 0
