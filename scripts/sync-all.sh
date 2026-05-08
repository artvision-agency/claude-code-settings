#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# sync-all.sh — Полная синхронизация Claude Code между аккаунтами
#
# Два канала синхронизации:
#   1. ~/.claude/ git repo → github.com/artvision-agency/claude-code-settings
#      (agents, hooks, rules, scripts, skills, tools, settings.json, CLAUDE.md)
#   2. projects/*/memory/ → artvision-data/.claude/memory-sync/
#      (per-project memory, включая MEMORY.md и все lessons-*.md)
#
# Использование:
#   sync-all.sh push    — отправить всё (по умолчанию)
#   sync-all.sh pull    — получить всё
#   sync-all.sh status  — показать что изменилось
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
ARTVISION_REPO="$HOME/artvision-data"
MEMORY_SYNC_DIR="$ARTVISION_REPO/.claude/memory-sync"
PROJECTS_DIR="$CLAUDE_DIR/projects"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok()    { echo -e "${GREEN}✅${NC} $1"; }
log_warn()  { echo -e "${YELLOW}⚠️${NC} $1"; }
log_err()   { echo -e "${RED}❌${NC} $1"; }
log_step()  { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }

# ─── TOKENS (через VPS, отдельный канал) ───────────────────

do_tokens() {
    local mode="$1"  # push|pull|sync
    log_step "tokens.json через VPS ($mode)"
    local script="$HOME/.claude/scripts/sync-tokens.sh"
    if [ -x "$script" ]; then
        timeout 30 "$script" "$mode" 2>&1 | tail -3 || log_warn "sync-tokens $mode exit=$?"
    else
        log_warn "sync-tokens.sh не установлен — пропускаю tokens"
    fi
}

# ─── PUSH ───────────────────────────────────────────────────

do_push() {
    local changes_made=0

    # ── Шаг 1: Коммит и пуш ~/.claude/ settings repo ──
    log_step "1/3 Settings repo (agents, hooks, rules, scripts, skills)"

    cd "$CLAUDE_DIR"

    # Добавить всё что не в gitignore
    git add -A

    if git diff --cached --quiet; then
        log_ok "Settings repo: нет изменений"
    else
        local changed_count
        changed_count=$(git diff --cached --stat | tail -1)
        log_info "Изменения: $changed_count"

        git commit -m "sync: full settings $(date +%Y-%m-%d_%H:%M)

Co-Authored-By: Claude <noreply@anthropic.com>"
        git push
        log_ok "Settings repo запушен"
        changes_made=1
    fi

    # ── Шаг 2: Синхронизация ВСЕЙ project memory ──
    log_step "2/3 Project memory (все проекты)"

    mkdir -p "$MEMORY_SYNC_DIR"

    local mem_changes=0

    # Перебираем все проекты с memory/
    if [ -d "$PROJECTS_DIR" ]; then
        for project_dir in "$PROJECTS_DIR"/*/; do
            [ -d "$project_dir" ] || continue

            local project_name
            project_name=$(basename "$project_dir")
            local project_mem="$project_dir/memory"

            if [ -d "$project_mem" ] && [ "$(ls -A "$project_mem" 2>/dev/null)" ]; then
                local dest="$MEMORY_SYNC_DIR/$project_name"
                mkdir -p "$dest"

                # rsync только memory файлы (не session logs)
                if rsync -av --delete "$project_mem/" "$dest/" 2>/dev/null | grep -q "^[^.]"; then
                    log_info "  📁 $project_name: synced"
                    mem_changes=1
                fi
            fi
        done
    fi

    if [ $mem_changes -eq 0 ]; then
        log_ok "Project memory: нет изменений"
    fi

    # ── Шаг 3: Коммит memory в artvision-data ──
    log_step "3/3 Коммит memory в artvision-data"

    cd "$ARTVISION_REPO"
    git add .claude/memory-sync/ 2>/dev/null || true

    if git diff --cached --quiet; then
        log_ok "Memory sync: нет изменений"
    else
        git commit -m "sync: all project memory $(date +%Y-%m-%d_%H:%M)

Co-Authored-By: Claude <noreply@anthropic.com>"
        git push
        log_ok "Memory запушена в artvision-data"
        changes_made=1
    fi

    # ── Шаг 4: tokens.json через VPS ──
    do_tokens push

    echo ""
    if [ $changes_made -eq 1 ]; then
        log_ok "Синхронизация завершена — всё запушено"
    else
        log_ok "Синхронизация завершена — изменений нет"
    fi
}

# ─── PULL ───────────────────────────────────────────────────

do_pull() {
    # ── Шаг 1: Получить settings repo ──
    log_step "1/2 Pulling settings repo"

    cd "$CLAUDE_DIR"

    # Сохранить локальные изменения если есть
    if ! git diff --quiet || ! git diff --cached --quiet; then
        log_warn "Есть локальные изменения — stashing"
        git stash
    fi

    git pull --ff-only
    log_ok "Settings repo обновлён"

    # ── Шаг 2: Получить memory из artvision-data ──
    log_step "2/2 Pulling project memory"

    cd "$ARTVISION_REPO"
    git pull --ff-only

    if [ -d "$MEMORY_SYNC_DIR" ]; then
        for project_mem_dir in "$MEMORY_SYNC_DIR"/*/; do
            [ -d "$project_mem_dir" ] || continue

            local project_name
            project_name=$(basename "$project_mem_dir")
            local dest="$PROJECTS_DIR/$project_name/memory"

            mkdir -p "$dest"
            rsync -av "$project_mem_dir/" "$dest/"
            log_info "  📁 $project_name: restored"
        done
        log_ok "Вся project memory восстановлена"
    else
        log_warn "Memory sync директория не найдена в artvision-data"
    fi

    # ── Шаг 3: tokens.json через VPS ──
    do_tokens pull

    echo ""
    log_ok "Pull завершён — всё актуально"
}

# ─── STATUS ─────────────────────────────────────────────────

do_status() {
    log_step "Settings repo"
    cd "$CLAUDE_DIR"
    git status --short

    log_step "Project memory"
    if [ -d "$PROJECTS_DIR" ]; then
        for project_dir in "$PROJECTS_DIR"/*/; do
            [ -d "$project_dir" ] || continue
            local project_name
            project_name=$(basename "$project_dir")
            local mem="$project_dir/memory"
            if [ -d "$mem" ] && [ "$(ls -A "$mem" 2>/dev/null)" ]; then
                local count
                count=$(find "$mem" -type f | wc -l | tr -d ' ')
                echo "  📁 $project_name: $count files"
            fi
        done
    fi

    log_step "Artvision-data memory-sync"
    if [ -d "$MEMORY_SYNC_DIR" ]; then
        for sync_dir in "$MEMORY_SYNC_DIR"/*/; do
            [ -d "$sync_dir" ] || continue
            local name
            name=$(basename "$sync_dir")
            local count
            count=$(find "$sync_dir" -type f | wc -l | tr -d ' ')
            echo "  📁 $name: $count files"
        done
    else
        echo "  (не создана)"
    fi
}

# ─── MAIN ───────────────────────────────────────────────────

case "${1:-push}" in
    push)   do_push   ;;
    pull)   do_pull   ;;
    status) do_status ;;
    *)
        echo "Использование: sync-all.sh [push|pull|status]"
        exit 1
        ;;
esac
