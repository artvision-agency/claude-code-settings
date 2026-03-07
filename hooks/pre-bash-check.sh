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

# === Блокировка scp/curl на серверы клиентов ===
# Тестовые файлы ТОЛЬКО на artvision.pro (80.90.181.152), НИКОГДА на серверы клиентов
# Два слоя: 1) блок известных серверов клиентов, 2) предупреждение о любом неизвестном IP
CLIENT_SERVERS="77\.222\.56\.111|ant\.partners|vh254\.timeweb\.ru"
OUR_VPS="80\.90\.181\.152|artvision\.pro|localhost|127\.0\.0\.1"
if echo "$COMMAND" | grep -qE "(scp|curl\s+(-T|--upload-file)|rsync)"; then
  if echo "$COMMAND" | grep -qE "$CLIENT_SERVERS"; then
    echo "[hook] БЛОКИРОВКА: загрузка на сервер КЛИЕНТА!"
    echo "[hook] Тестовые файлы → ТОЛЬКО на 80.90.181.152 (artvision.pro)"
    echo "[hook] Команда: $COMMAND"
    exit 2
  fi
  if ! echo "$COMMAND" | grep -qE "$OUR_VPS" && echo "$COMMAND" | grep -qE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"; then
    echo "[hook] ВНИМАНИЕ: загрузка на неизвестный IP! Проверь что это наш сервер."
    echo "[hook] Разрешённые: 80.90.181.152, artvision.pro"
    echo "[hook] Команда: $COMMAND"
  fi
fi

# === Блокировка sed -i на functions.php ===
if echo "$COMMAND" | grep -qE "sed\s+(-i|--in-place)" && echo "$COMMAND" | grep -q "functions.php"; then
  echo "[hook] БЛОКИРОВКА: sed на functions.php опасен (кавычки потеряются → 500)!"
  echo "[hook] Используй mu-plugin: wp-content/mu-plugins/custom.php"
  exit 2
fi

# === Предупреждение при деплое ботов без проверки локальных процессов ===
if echo "$COMMAND" | grep -qE "(scp|rsync).*bot\.py.*80\.90\.181\.152" || echo "$COMMAND" | grep -qE "systemctl\s+(restart|start)\s+.*bot"; then
  LOCAL_BOTS=$(ps aux 2>/dev/null | grep "[b]ot.py" | grep -v deploy | grep -v grep || true)
  if [ -n "$LOCAL_BOTS" ]; then
    echo "[hook] ВНИМАНИЕ: обнаружен локальный bot.py процесс!"
    echo "[hook] Это вызовет 409 Conflict с VDS. Убей локальный процесс или используй deploy.sh"
    echo "$LOCAL_BOTS" | head -3
  fi
fi

# === Предупреждение о pip install без venv ===
if echo "$COMMAND" | grep -qE "pip3?\s+install" && ! echo "$COMMAND" | grep -q "venv\|--user"; then
  if [ -z "$VIRTUAL_ENV" ]; then
    echo "[hook] pip install вне virtualenv — пакеты установятся глобально."
  fi
fi

exit 0
