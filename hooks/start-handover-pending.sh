#!/bin/bash
# start-handover-pending.sh — при старте новой сессии проверяет .pending
# маркеры от stop-handover-check.sh и напоминает Claude создать handover
# для предыдущих substantive сессий без handover.
#
# Вывод идёт в stdout → инжектится в контекст Claude.

set -uo pipefail

PENDING_DIR="$HOME/.claude/handovers/.pending"

if [ ! -d "$PENDING_DIR" ]; then
    exit 0
fi

# Список pending маркеров (исключая текущую сессию если вдруг попала)
SESSIONS_DIR="$HOME/.claude/projects/-Users-antonk"
CURRENT_JSONL=$(ls -t "$SESSIONS_DIR"/*.jsonl 2>/dev/null | head -1 || true)
CURRENT_SID=""
if [ -n "${CURRENT_JSONL:-}" ]; then
    CURRENT_SID=$(basename "$CURRENT_JSONL" .jsonl)
fi

MARKERS=()
while IFS= read -r -d '' f; do
    sid=$(basename "$f")
    [ "$sid" = "$CURRENT_SID" ] && continue
    MARKERS+=("$f")
done < <(find "$PENDING_DIR" -maxdepth 1 -type f -print0 2>/dev/null)

if [ "${#MARKERS[@]}" -eq 0 ]; then
    exit 0
fi

echo "═══════════════════════════════════════════"
echo "  ⚠️  PENDING HANDOVERS: ${#MARKERS[@]} substantive сессия(й) без handover"
echo "═══════════════════════════════════════════"
echo ""
echo "Предыдущие сессии были substantive (много Edit/Write/Bash или >15 мин), но handover не создан."
echo "Для каждой нужно: прочитать transcript → написать HANDOVER-*.md → rm маркер."
echo ""

for m in "${MARKERS[@]}"; do
    sid=$(basename "$m")
    echo "--- $sid ---"
    cat "$m" 2>/dev/null | sed 's/^/  /'
    echo ""
done

echo "Действие:"
echo "  1. Прочитай transcript из поля 'transcript=' для каждого маркера"
echo "  2. Создай HANDOVER-YYYY-MM-DD-HHMM-<context>.md через skill handover"
echo "     (в frontmatter ОБЯЗАТЕЛЬНО session_id=<тот же UUID>)"
echo "  3. rm маркер: rm \$HOME/.claude/handovers/.pending/<session_id>"
echo ""
echo "Если сессия уже неактуальна — просто rm маркер без handover."
echo "═══════════════════════════════════════════"

exit 0
