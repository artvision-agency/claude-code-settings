#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# todo.sh — Показать TODO из всех контекстов
#
# Использование:
#   todo.sh          — показать все TODO
#   todo.sh ops      — только ops
#   todo.sh bot      — только bot
#   todo.sh infra    — только infra
#   todo.sh presale  — только presale
#   todo.sh products — только products
#
# 0 токенов Claude. Совместимо с macOS bash 3.2.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

get_todo_file() {
    case "$1" in
        ops)      echo "$HOME/artvision-data/TODO.md" ;;
        bot)      echo "$HOME/artvision-tg-bot/TODO.md" ;;
        infra)    echo "$HOME/devops-agent/TODO.md" ;;
        presale)  echo "$HOME/artvision-data/presale/TODO.md" ;;
        products) echo "$HOME/artvision-data/products/TODO.md" ;;
        *)        echo "" ;;
    esac
}

show_todo() {
    local ctx="$1"
    local file
    file=$(get_todo_file "$ctx")

    if [ -z "$file" ] || [ ! -f "$file" ]; then
        echo -e "  ${YELLOW}(файл не найден)${NC}"
        return
    fi

    local pending=0 done=0
    pending=$(grep -c '^\- \[ \]' "$file" 2>/dev/null || true)
    done=$(grep -c '^\- \[x\]' "$file" 2>/dev/null || true)
    # macOS grep -c returns empty on 0 matches
    pending=${pending:-0}
    done=${done:-0}

    echo -e "${BLUE}━━━ $ctx${NC} ($file)"
    echo -e "  Открыто: ${YELLOW}$pending${NC} | Готово: ${GREEN}$done${NC}"

    if [ "$pending" -gt 0 ] 2>/dev/null; then
        grep '^\- \[ \]' "$file" | head -15 | while IFS= read -r line; do
            echo -e "  ${RED}○${NC} ${line#- \[ \] }"
        done
    else
        echo -e "  ${GREEN}Всё выполнено!${NC}"
    fi
    echo ""
}

filter="${1:-all}"

if [ "$filter" = "all" ]; then
    echo -e "\n${BLUE}═══ TODO — все контексты ═══${NC}\n"
    for ctx in ops presale products bot infra; do
        show_todo "$ctx"
    done
else
    case "$filter" in
        ops|bot|infra|presale|products)
            echo ""
            show_todo "$filter"
            ;;
        *)
            echo "Контексты: ops, bot, infra, presale, products, all"
            exit 1
            ;;
    esac
fi
