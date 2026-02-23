#!/bin/bash
# PreToolUse (Bash): проверки перед выполнением команд
# 1. tmux напоминание для долгих команд
# 2. Защита от rm -rf на важных путях
# 3. Предупреждение о деструктивных git операциях

COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

if [ -z "$COMMAND" ]; then
  exit 0
fi

# === tmux напоминание для долгих команд ===
if echo "$COMMAND" | grep -qE "(npm (run|install|test|build)|pnpm|yarn|cargo (build|test)|pytest|playwright|webpack|vite build|docker build|pip install)"; then
  if [ -z "$TMUX" ]; then
    echo "[hook] Длинная команда вне tmux. Если терминал отключится — работа пропадёт."
    echo "[hook] Совет: tmux new -s work && запустите команду внутри"
  fi
fi

# === Защита от опасного rm ===
if echo "$COMMAND" | grep -qE "rm\s+(-rf?|--recursive)\s+(/Users|~/artvision|~/devops|\.\./|/Users/antonk/(artvision|devops))"; then
  echo "[hook] ОПАСНО: rm -rf на критическом пути!"
  echo "[hook] Команда: $COMMAND"
  exit 2
fi

# === Предупреждение о деструктивных git ===
if echo "$COMMAND" | grep -qE "git\s+(push\s+--force|reset\s+--hard|clean\s+-f|checkout\s+\.)"; then
  echo "[hook] Деструктивная git операция: $COMMAND"
  echo "[hook] Это необратимо. Убедитесь что это намеренно."
fi

# === Предупреждение о pip install без venv ===
if echo "$COMMAND" | grep -qE "pip3?\s+install" && ! echo "$COMMAND" | grep -q "venv\|--user"; then
  if [ -z "$VIRTUAL_ENV" ]; then
    echo "[hook] pip install вне virtualenv — пакеты установятся глобально."
  fi
fi

exit 0
