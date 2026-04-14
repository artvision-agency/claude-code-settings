#!/bin/bash
# combine-auto-evening.sh — авторежим комбайна, вечерний прогон 18:00
# Запускается LaunchAgent pro.artvision.combine-evening
#
# Что делает:
#   1. combine ревью — анализ прогресса за день
#   2. Самосовершенствование (патчи клиентов, предложения в rules/)
#   3. Отчёт дня + предложения → TG Антону
#   4. Финальный git push

set -euo pipefail

LOG_DIR="$HOME/Library/Logs"
LOG_FILE="$LOG_DIR/combine-auto.log"
DATE=$(date +%Y-%m-%d)

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [evening] $*" | tee -a "$LOG_FILE"
}

log "=== START evening run ==="

# 1. Pull свежих изменений
for repo in artvision-data artvision-tg-bot devops-agent; do
    dir="$HOME/$repo"
    if [ -d "$dir/.git" ]; then
        (cd "$dir" && git pull --ff-only 2>&1 | tee -a "$LOG_FILE") || log "pull FAILED $repo"
    fi
done

# 2. Комбайн ревью + предложения
PROMPT="комбайн ревью — анализ дня ${DATE}. Прочитай reports/combine-${DATE}-morning.md если есть.
Составь:
1. Что выполнено, что зависло
2. Паттерны ошибок → patches/ клиентов (AUTO)
3. Предложения в rules/ и skills/ (показать, НЕ применять)
4. Отчёт дня → reports/combine-${DATE}-evening.md
5. В TG Антону — краткая сводка + предложения"

if command -v claude >/dev/null 2>&1; then
    log "combine review start"
    cd "$HOME/artvision-data"
    claude --print "$PROMPT" >> "$LOG_FILE" 2>&1 || log "combine review exited non-zero"
    log "combine review done"
else
    log "ERROR: claude CLI not found"
    exit 1
fi

# 3. Отчёт в TG
REPORT_FILE="$HOME/artvision-data/reports/combine-${DATE}-evening.md"
if [ -f "$REPORT_FILE" ]; then
    if [ -x "$HOME/.claude/scripts/tg-send.sh" ]; then
        log "send evening report to TG"
        "$HOME/.claude/scripts/tg-send.sh" "anton" "$(cat "$REPORT_FILE")" || log "TG send FAILED"
    fi
fi

# 4. Финальный git push по всем репо
for repo in artvision-data artvision-tg-bot devops-agent; do
    dir="$HOME/$repo"
    if [ -d "$dir/.git" ]; then
        cd "$dir"
        if [ -n "$(git status --porcelain 2>/dev/null || true)" ]; then
            log "commit + push $repo"
            git add -A
            git commit -m "chore(combine): auto evening ${DATE}

Co-Authored-By: Claude <noreply@anthropic.com>" || true
            git push || log "push FAILED $repo"
        fi
    fi
done

log "=== END evening run ==="
