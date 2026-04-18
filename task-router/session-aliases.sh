#!/bin/bash
# Алиасы для запуска именованных сессий Claude Code
# Использование: source ~/.claude/task-router/session-aliases.sh

# Флаги — skip permissions + channels по дефолту
_CC='--dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official'

# Именованные сессии (все с TG каналом + auto mode)
alias cc-ops="cd /Users/antonk/artvision-data && claude $_CC --continue"
alias cc-bot="cd /Users/antonk/artvision-tg-bot && claude $_CC --continue"
alias cc-devops="cd /Users/antonk/devops-agent && claude $_CC --continue"
alias cc-products="cd /Users/antonk/artvision-data && claude $_CC --continue"
alias cc-presale="cd /Users/antonk/artvision-data && claude $_CC --continue"
alias cc-hub="cd /Users/antonk && claude $_CC --continue"

# Новая сессия (чистая)
alias cc-ops-new="cd /Users/antonk/artvision-data && claude $_CC"
alias cc-bot-new="cd /Users/antonk/artvision-tg-bot && claude $_CC"
alias cc-devops-new="cd /Users/antonk/devops-agent && claude $_CC"

# Список сессий
alias cc-list='echo "=== Claude Sessions (auto mode + TG) ===" && echo "" && echo "  cc-ops      → artvision-data" && echo "  cc-bot      → artvision-tg-bot" && echo "  cc-devops   → devops-agent" && echo "  cc-products → artvision-data" && echo "  cc-presale  → artvision-data" && echo "  cc-hub      → ~ (хаб)" && echo "" && echo "Новые:" && echo "  cc-ops-new / cc-bot-new / cc-devops-new"'
