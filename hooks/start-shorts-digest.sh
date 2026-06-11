#!/bin/bash
# start-shorts-digest.sh — SessionStart: компактная сводка по шортсам в стартовом меню.
# Полный дайджест уходит в TG в 09:00 (pro.artvision.shorts-digest). Здесь — короткий блок.
# Регенерирует снимок если он старше 20ч (на случай если LaunchAgent не сработал).
set -uo pipefail

SNAP="$HOME/.claude/data/shorts-digest-latest.txt"
SCRIPT="$HOME/.claude/scripts/shorts-daily-digest.py"
QUEUE="$HOME/.claude/data/shorts-queue.tsv"

# регенерация снимка без TG, если старый/нет (тихо, не блокируя старт)
if [ ! -f "$SNAP" ] || [ -n "$(find "$SNAP" -mmin +1200 2>/dev/null)" ]; then
    python3 "$SCRIPT" --no-tg >/dev/null 2>&1 &
fi

# если снимок есть — показать первые блоки (очередь + залито вчера)
ready=0; hold=0
if [ -f "$QUEUE" ]; then
    ready=$(awk -F'\t' '!/^#/ && $3=="ready"{n++} END{print n+0}' "$QUEUE")
    hold=$(awk -F'\t' '!/^#/ && $3=="hold"{n++} END{print n+0}' "$QUEUE")
fi

echo "═══════════════════════════════════════════"
echo "  📹 ШОРТСЫ @-Artvisionpro"
if [ -f "$SNAP" ]; then
    # строка про залито вчера + последняя заливка
    grep -E "Залито вчера|Последняя заливка|Всего на канале" "$SNAP" 2>/dev/null | head -2 | sed 's/^/  /'
fi
echo "  Очередь: ${ready} ready · ${hold} hold"
if [ "$ready" -gt 0 ]; then
    awk -F'\t' '!/^#/ && $3=="ready"{print "    ✅ "$2}' "$QUEUE" | head -2
    echo "  → «залей шортс из очереди» чтобы опубликовать"
fi
echo "  Полный дайджест — в TG (09:00) · 🔗 youtube.com/@-Artvisionpro/shorts"
echo "═══════════════════════════════════════════"
exit 0
