#!/bin/bash
# sync-accounts.sh — Синхронизация настроек Claude Code между аккаунтами
# Оба аккаунта на одной машине /Users/antonk/
#
# РЕЗУЛЬТАТ ИССЛЕДОВАНИЯ (2026-03-27):
# ==========================================
# ОБЩИЕ (одна папка на диске, работают для ОБОИХ аккаунтов):
#   ~/.claude/rules/          -- все rules загружаются для любого аккаунта
#   ~/.claude/skills/         -- все skills доступны для любого аккаунта
#   ~/.claude/hooks/          -- хуки в settings.json работают для обоих
#   ~/.claude/scripts/        -- скрипты на диске, общие
#   ~/.claude/agents/         -- справочник агентов, общий
#   ~/.claude/CLAUDE.md       -- глобальные инструкции, общие
#   ~/.claude/settings.json   -- конфиг с permissions/hooks, общий
#   ~/.claude/commands/       -- slash-команды, общие
#
# ПРИВЯЗАНЫ К АККАУНТУ (через Claude API, НЕ файлы):
#   memory (auto-memory)      -- хранится на серверах Anthropic per-account
#                                ~/.claude/projects/*/memory/ -- ЛОКАЛЬНЫЙ КЕШ
#                                При переключении аккаунта -- другой memory на сервере
#
# НЕ привязаны к аккаунту, но per-session:
#   ~/.claude/projects/*/     -- сессии привязаны к cwd, не к аккаунту
#   ~/.claude/sessions/       -- PID текущих сессий
#   settings.local.json       -- локальные permissions (per-machine)
#
# ВЫВОД: Проблема "голого" justtrance НЕ в файлах (файлы общие),
#         а в auto-memory на серверах Anthropic.
#         rules/skills/hooks/settings работают одинаково для обоих.
# ==========================================

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
MEMORY_DIR="$CLAUDE_DIR/projects/-Users-antonk/memory"
ARTVISION_MEMORY_SYNC="$HOME/artvision-data/.claude/memory-sync"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Claude Code Account Sync ===${NC}"
echo ""

# 1. Check current account
echo -e "${YELLOW}1. Текущий аккаунт:${NC}"
CURRENT_ACCOUNT=$(CLAUDECODE= claude auth status 2>&1 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('email', 'unknown'))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")
echo "   $CURRENT_ACCOUNT"
echo ""

# 2. Verify shared components
echo -e "${YELLOW}2. Общие компоненты (работают для ОБОИХ аккаунтов):${NC}"

check_dir() {
    local dir="$1"
    local name="$2"
    if [ -d "$dir" ]; then
        local count=$(ls -1 "$dir" 2>/dev/null | wc -l | tr -d ' ')
        echo -e "   ${GREEN}OK${NC} $name ($count items)"
    else
        echo -e "   ${RED}MISSING${NC} $name"
    fi
}

check_file() {
    local file="$1"
    local name="$2"
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}OK${NC} $name"
    else
        echo -e "   ${RED}MISSING${NC} $name"
    fi
}

check_dir "$CLAUDE_DIR/rules" "rules/"
check_dir "$CLAUDE_DIR/skills" "skills/"
check_dir "$CLAUDE_DIR/hooks" "hooks/"
check_dir "$CLAUDE_DIR/scripts" "scripts/"
check_dir "$CLAUDE_DIR/agents" "agents/"
check_dir "$CLAUDE_DIR/commands" "commands/"
check_file "$CLAUDE_DIR/CLAUDE.md" "CLAUDE.md"
check_file "$CLAUDE_DIR/settings.json" "settings.json"
check_file "$CLAUDE_DIR/settings.local.json" "settings.local.json"
echo ""

# 3. Check memory sync status
echo -e "${YELLOW}3. Auto-memory (привязана к АККАУНТУ на серверах Anthropic):${NC}"
if [ -d "$MEMORY_DIR" ]; then
    MEMORY_COUNT=$(ls -1 "$MEMORY_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    echo -e "   Локальный кеш memory: ${GREEN}$MEMORY_COUNT файлов${NC}"
    echo "   ВАЖНО: это кеш для текущего аккаунта ($CURRENT_ACCOUNT)"
    echo "   При переключении -- сервер Anthropic отдаст memory другого аккаунта"
else
    echo -e "   ${RED}Нет локального кеша memory${NC}"
fi
echo ""

# 4. Memory content sync via git
echo -e "${YELLOW}4. Синхронизация memory через git:${NC}"
if [ -d "$ARTVISION_MEMORY_SYNC" ]; then
    SYNC_COUNT=$(ls -1 "$ARTVISION_MEMORY_SYNC"/*.md 2>/dev/null | wc -l | tr -d ' ')
    echo -e "   Git-зеркало memory: ${GREEN}$SYNC_COUNT файлов${NC}"
else
    echo -e "   ${RED}Git-зеркало НЕ создано${NC}"
    echo "   Запусти: ~/.claude/scripts/sync-memory.sh push"
fi
echo ""

# 5. Export critical memory entries
echo -e "${YELLOW}5. Критические memory-записи:${NC}"
CRITICAL_MEMORIES=(
    "MEMORY.md"
    "accounts.md"
    "clients-status.md"
    "infrastructure.md"
    "revenue-goal.md"
    "products-status.md"
    "interaction-patterns.md"
    "shortcuts.md"
)

MISSING=0
for mem in "${CRITICAL_MEMORIES[@]}"; do
    if [ -f "$MEMORY_DIR/$mem" ]; then
        echo -e "   ${GREEN}OK${NC} $mem"
    else
        echo -e "   ${RED}MISSING${NC} $mem"
        MISSING=$((MISSING + 1))
    fi
done
echo ""

# 6. Summary
echo -e "${BLUE}=== ИТОГО ===${NC}"
echo ""
echo "Для justtrance@gmail.com:"
echo "  1. rules/skills/hooks/settings -- УЖЕ работают (общие файлы)"
echo "  2. auto-memory -- НУЖНО инициализировать при первом запуске"
echo "     Способ: попросить Claude прочитать ~/.claude/projects/-Users-antonk/memory/"
echo "  3. Между сессиями: ~/.claude/scripts/sync-memory.sh sync"
echo ""
echo -e "${GREEN}Готово.${NC}"
