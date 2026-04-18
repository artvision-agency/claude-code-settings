#!/bin/bash
# link-digest.sh — ежедневный (09:00) и еженедельный (ВС 10:00) дайджест.
#
# $1: daily | weekly

set -euo pipefail

MODE="${1:-daily}"
LOGFILE="$HOME/.claude/logs/link-digest-$(date +%Y-%m-%d).log"
mkdir -p "$(dirname "$LOGFILE")"

log() { echo "$(date '+%H:%M:%S') $*" >> "$LOGFILE"; }
log "=== $MODE digest start ==="

cd "$HOME/artvision-data"

if [ "$MODE" = "daily" ]; then
    PROMPT='Собери daily digest ссылок. 1) python3 ~/.claude/scripts/link-inbox-query.py через REST — выбери все link_inbox за последние 24ч со status=processed. 2) Для каждой — коротко (1 строка): emoji платформы + title + ключевое "для нас". 3) Сгруппируй по тегам. 4) Отправь мне (chat_id 161261562) через curl к TG Bot API. Длина: до 3500 символов. Формат HTML.'
elif [ "$MODE" = "weekly" ]; then
    PROMPT='Собери weekly digest ссылок за последние 7 дней. 1) Все processed ссылки → сгруппируй по темам (Claude/AI-tools, marketing, seo, products). 2) Выдели 3-5 главных инсайтов применимых к нашим продуктам (AIvision, Card Duel, Direct-Radar, SEO Pipeline). 3) Отдельный блок: "durable knowledge записанный в memory за неделю" (из ~/.claude/projects/-Users-antonk/memory/ по mtime > 7d). 4) Отправь мне (chat_id 161261562) через TG Bot API. Длина до 4000 символов.'
else
    echo "Unknown mode: $MODE" >&2
    exit 1
fi

OUTPUT=$(claude --print \
    --permission-mode bypassPermissions \
    --output-format text \
    "$PROMPT" 2>&1 || echo "CLAUDE_FAILED: $?")

echo "$OUTPUT" | tail -30 >> "$LOGFILE"
log "=== $MODE digest done ==="
