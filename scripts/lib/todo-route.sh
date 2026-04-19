#!/bin/bash
# Shared TODO routing logic — single source for cwd→TODO mapping.
# Sourced by: hooks/start-todo-taskcreate.sh, combine script, sync-sessions script.
#
# Usage:
#   source ~/.claude/scripts/lib/todo-route.sh
#   read TODO CTX < <(todo_for_cwd "$PWD")
#
# Routes (first match wins):
#   */artvision-data/presale*  → presale/TODO.md
#   */artvision-data/products* → products/TODO.md
#   */artvision-data*          → ops TODO.md
#   */artvision-tg-bot*        → bot TODO.md
#   */devops-agent*            → infra TODO.md
#   default                    → ops TODO.md

# shellcheck disable=SC2120  # may be called with or without arg
todo_for_cwd() {
    local cwd="${1:-$PWD}"
    local todo ctx
    case "$cwd" in
        */artvision-data/presale*)  todo=/Users/antonk/artvision-data/presale/TODO.md;  ctx=presale ;;
        */artvision-data/products*) todo=/Users/antonk/artvision-data/products/TODO.md; ctx=products ;;
        */artvision-data*)          todo=/Users/antonk/artvision-data/TODO.md;          ctx=ops ;;
        */artvision-tg-bot*)        todo=/Users/antonk/artvision-tg-bot/TODO.md;        ctx=bot ;;
        */devops-agent*)            todo=/Users/antonk/devops-agent/TODO.md;            ctx=infra ;;
        *)                          todo=/Users/antonk/artvision-data/TODO.md;          ctx=ops ;;
    esac
    printf '%s\t%s\n' "$todo" "$ctx"
}

# When sourced without a call, expose function. When executed directly, emit mapping.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    todo_for_cwd "$@"
fi
