#!/bin/bash
# start-handover-pending.sh — компактное напоминание о pending handovers.
#
# v2 (2026-04-25): не дампит full content всех маркеров (раньше = ~250 строк
# контекста при 29 маркерах). Показывает count + top-5 last detected.
# Полный список — в `~/.claude/handovers/.pending/`.

set -uo pipefail

PENDING_DIR="$HOME/.claude/handovers/.pending"
[ ! -d "$PENDING_DIR" ] && exit 0

SESSIONS_DIR="$HOME/.claude/projects/-Users-antonk"
CURRENT_JSONL=$(ls -t "$SESSIONS_DIR"/*.jsonl 2>/dev/null | head -1 || true)
CURRENT_SID=""
[ -n "${CURRENT_JSONL:-}" ] && CURRENT_SID=$(basename "$CURRENT_JSONL" .jsonl)

# Собираем маркеры с mtime, исключая текущую сессию
MARKERS=()
while IFS= read -r f; do
    sid=$(basename "$f")
    [ "$sid" = "$CURRENT_SID" ] && continue
    MARKERS+=("$f")
done < <(find "$PENDING_DIR" -maxdepth 1 -type f 2>/dev/null)

COUNT=${#MARKERS[@]}
[ "$COUNT" -eq 0 ] && exit 0

# Top-5 last by mtime
TOP5=$(ls -t "${MARKERS[@]}" 2>/dev/null | head -5)

echo "⚠️  Pending handovers: $COUNT substantive сессий без HANDOVER.md"
echo "    Last 5 (by detected_at):"
while IFS= read -r f; do
    sid=$(basename "$f")
    # Извлекаем cwd_hint и duration_min для одной строки
    cwd=$(grep '^cwd_hint=' "$f" 2>/dev/null | head -1 | cut -d= -f2- | sed 's|/Users/antonk||')
    dur=$(grep '^duration_min=' "$f" 2>/dev/null | head -1 | cut -d= -f2)
    echo "      ${sid:0:8}  ${cwd:-?}  ${dur:-?}min"
done <<< "$TOP5"
echo "    Полный список: ls $PENDING_DIR/"
echo "    Чтобы разгрести — Skill handover для каждого + rm маркер."

exit 0
