#!/bin/bash
# combine-auto-morning.sh — авторежим комбайна, утренний прогон 09:30
# Запускается LaunchAgent pro.artvision.combine-morning
#
# Что делает:
#   1. git pull всех 3 репо
#   2. combine без интерактива — все AUTO выполняются
#   3. CONFIRM-задачи собираются в батч, отправляются в TG группу команды
#   4. Отчёт → reports/ + TG

set -euo pipefail

LOG_DIR="$HOME/Library/Logs"
LOG_FILE="$LOG_DIR/combine-auto.log"
DATE=$(date +%Y-%m-%d)
HOUR=$(date +%H:%M)

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [morning] $*" | tee -a "$LOG_FILE"
}

log "=== START morning run ==="

# 1. Git pull всех репо
for repo in artvision-data artvision-tg-bot devops-agent; do
    dir="$HOME/$repo"
    if [ -d "$dir/.git" ]; then
        log "pull $repo"
        (cd "$dir" && git pull --ff-only 2>&1 | tee -a "$LOG_FILE") || log "pull FAILED $repo"
    fi
done

# 2. Запуск комбайна через claude CLI (неинтерактивно)
# claude --print читает prompt, выполняет, выходит
PROMPT="комбайн авто утро — выполни все AUTO-задачи из очереди. CONFIRM собери в батч для TG. Отчёт в artvision-data/reports/combine-${DATE}-morning.md"

if command -v claude >/dev/null 2>&1; then
    log "combine start"
    cd "$HOME/artvision-data"
    claude --print "$PROMPT" >> "$LOG_FILE" 2>&1 || log "combine exited non-zero"
    log "combine done"
else
    log "ERROR: claude CLI not found in PATH"
    exit 1
fi

# 3. Отчёт в TG
REPORT_FILE="$HOME/artvision-data/reports/combine-${DATE}-morning.md"
if [ -f "$REPORT_FILE" ]; then
    if [ -x "$HOME/.claude/scripts/tg-send.sh" ]; then
        log "send report to TG"
        "$HOME/.claude/scripts/tg-send.sh" "team" "$(cat "$REPORT_FILE")" || log "TG send FAILED"
    else
        log "tg-send.sh not found, skipping TG"
    fi
else
    log "no report file at $REPORT_FILE"
fi

# 4. Push TODO + reports
cd "$HOME/artvision-data"
if [ -n "$(git status --porcelain TODO.md reports/ 2>/dev/null || true)" ]; then
    log "push TODO + reports"
    git add TODO.md reports/ presale/TODO.md products/TODO.md 2>/dev/null || true
    git commit -m "chore(combine): auto morning ${DATE}

Co-Authored-By: Claude <noreply@anthropic.com>" || log "nothing to commit"
    git push || log "push FAILED"
fi

log "=== END morning run ==="
