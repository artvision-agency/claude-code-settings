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

# Early exit: claude-invocation обрабатывает ТОЛЬКО link_inbox --pending.
# Если там 0 — выходим, независимо от asana-pending (его обработает отдельный механизм).
# Фикс 2026-04-21: экономия ~50-80K токенов × N вызовов впустую.
if [ "$COUNT" = "0" ]; then
    # Лог только для asana-pending сигнала (диагностика), но claude НЕ вызываем
    ASANA_PENDING=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --asana-pending --limit 1 2>/dev/null || echo "[]")
    A_COUNT=$(echo "$ASANA_PENDING" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "$A_COUNT" != "0" ]; then
        log "note: $A_COUNT asana-pending есть, но claude-invocation — только для link_inbox. Skip."
    fi
    exit 0
fi

LINK_ID=$(echo "$PENDING" | python3 -c "import sys,json; rows=json.load(sys.stdin); print(rows[0]['id'] if rows else '')" 2>/dev/null || echo "")
if [ -z "$LINK_ID" ]; then
    log "skip: pending row has no id"
    exit 0
fi

# Persistent retry gate: 5m after attempt 1, 15m after attempt 2, failed after attempt 3.
RETRY=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --retry-check "$LINK_ID" 2>/dev/null || echo '{"eligible":false,"reason":"retry-check-failed"}')
ELIGIBLE=$(echo "$RETRY" | python3 -c "import sys,json; print('yes' if json.load(sys.stdin).get('eligible') else 'no')" 2>/dev/null || echo "no")
if [ "$ELIGIBLE" != "yes" ]; then
    log "skip: retry gate blocks id=$LINK_ID state=$RETRY"
    exit 0
fi

# Reserve exactly one row so another worker cannot pick it concurrently.
if ! python3 "$HOME/.claude/scripts/link-inbox-query.py" --mark-processing "$LINK_ID" >> "$LOGFILE" 2>&1; then
    log "skip: could not reserve id=$LINK_ID"
    exit 0
fi

log "found pending id=$LINK_ID — invoking Claude Code"

# Запускаем Claude Code в headless режиме из artvision-data (чтобы загрузился контекст)
cd "$HOME/artvision-data"

PROMPT="Выполни skill process-link только для link_inbox id=$LINK_ID. Получи строку через python3 ~/.claude/scripts/link-inbox-query.py --get '$LINK_ID'. Сделай fetch → factcheck → карточка → memory (если durable) → UPDATE status=processed + editMessageText. Другие строки не обрабатывай. Работай автономно, без вопросов."

# --print = non-interactive, --permission-mode bypassPermissions = без спросов
# --output-format text = читаемый вывод для лога
set +e
OUTPUT=$(claude --print \
    --permission-mode bypassPermissions \
    --output-format text \
    --append-system-prompt "Ты запущен link-processor.sh. Цель: обработать pending-ссылки через skill process-link. Никаких вопросов, работай молча." \
    "$PROMPT" 2>&1)
CLAUDE_RC=$?
set -e

# Последние 20 строк вывода в лог
echo "$OUTPUT" | tail -20 >> "$LOGFILE"
log "claude -p complete"

# Hard stop: oversized prompt must never be retried. Other errors get 5m/15m backoff,
# and the third failure becomes terminal. Local retry state blocks loops even if DB is down.
if [ "$CLAUDE_RC" -ne 0 ] || echo "$OUTPUT" | grep -qi "Prompt is too long"; then
    ERROR_MSG=$(printf '%s' "$OUTPUT" | tail -20 | head -c 900)
    [ -n "$ERROR_MSG" ] || ERROR_MSG="Claude exited with code $CLAUDE_RC"
    python3 "$HOME/.claude/scripts/link-inbox-query.py" --record-failure "$LINK_ID" --error-msg "$ERROR_MSG" >> "$LOGFILE" 2>&1 || true
    log "claude failed id=$LINK_ID rc=$CLAUDE_RC; retry policy applied"
    exit 0
fi

ROW=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --get "$LINK_ID" 2>/dev/null || echo '{}')
ROW_STATUS=$(echo "$ROW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
if [ "$ROW_STATUS" != "processed" ]; then
    python3 "$HOME/.claude/scripts/link-inbox-query.py" --record-failure "$LINK_ID" --error-msg "Claude exited 0 but row status=$ROW_STATUS" >> "$LOGFILE" 2>&1 || true
    log "incomplete id=$LINK_ID status=$ROW_STATUS; retry policy applied"
    exit 0
fi

python3 "$HOME/.claude/scripts/link-inbox-query.py" --clear-retry "$LINK_ID" >> "$LOGFILE" 2>&1 || true

# FINALIZE — дожим: карточка в TG + learning/links/YYYY-MM.md + memory/trend_*.md
# Для всех processed-строк без learning_file (claude мог не дожать последние шаги skill)
FINALIZE_OUT=$(python3 "$HOME/.claude/scripts/link-inbox-query.py" --finalize 2>&1 || echo "finalize_failed: $?")
echo "$FINALIZE_OUT" >> "$LOGFILE"
log "run complete"
