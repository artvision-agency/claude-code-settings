#!/bin/bash
# link-processor.sh — обработка pending ссылок из link_inbox через Claude Code (Max 20x).
#
# Запускается LaunchAgent'ом pro.artvision.link-processor каждые 60 сек.
# Idempotent: если нет pending — выходит без работы. PID lock от наложений.

set -euo pipefail

LOCKFILE="/tmp/link-processor.lock"
LOGDIR="$HOME/.claude/logs"
TODAY=$(date +%Y-%m-%d)
LOGFILE="$LOGDIR/link-processor-$TODAY.log"
mkdir -p "$LOGDIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOGFILE"
}

# PID lock — если предыдущий прогон ещё идёт, выходим
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE" 2>/dev/null || echo "")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        log "skip: another run in progress (pid=$PID)"
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# Проверка pending
PENDING=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --pending --limit 1 2>/dev/null || echo "[]")
COUNT=$(echo "$PENDING" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

if [ "$COUNT" = "0" ]; then
    # Проверим asana-pending (пользователь нажал 📌 после обработки)
    ASANA_PENDING=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --asana-pending --limit 1 2>/dev/null || echo "[]")
    A_COUNT=$(echo "$ASANA_PENDING" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "$A_COUNT" = "0" ]; then
        exit 0
    fi
    log "found $A_COUNT asana-pending"
fi

log "found $COUNT pending link(s) — invoking Claude Code"

# Запускаем Claude Code в headless режиме из artvision-data (чтобы загрузился контекст)
cd "$HOME/artvision-data"

PROMPT='Выполни skill process-link. Обработай все pending-строки из таблицы link_inbox (через python3 ~/.claude/scripts/link-inbox-query.py --pending --limit 5). Для каждой: fetch → factcheck → карточка → memory (если durable) → UPDATE + editMessageText. Работай автономно, без вопросов. После обработки всех — выйди.'

# --print = non-interactive, --permission-mode bypassPermissions = без спросов
# --output-format text = читаемый вывод для лога
OUTPUT=$(claude --print \
    --permission-mode bypassPermissions \
    --output-format text \
    --append-system-prompt "Ты запущен link-processor.sh. Цель: обработать pending-ссылки через skill process-link. Никаких вопросов, работай молча." \
    "$PROMPT" 2>&1 || echo "CLAUDE_FAILED: $?")

# Последние 20 строк вывода в лог
echo "$OUTPUT" | tail -20 >> "$LOGFILE"
log "claude -p complete"

# FINALIZE — дожим: карточка в TG + learning/links/YYYY-MM.md + memory/trend_*.md
# Для всех processed-строк без learning_file (claude мог не дожать последние шаги skill)
FINALIZE_OUT=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --finalize 2>&1 || echo "finalize_failed: $?")
echo "$FINALIZE_OUT" >> "$LOGFILE"
log "run complete"
