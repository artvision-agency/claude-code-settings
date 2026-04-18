#!/bin/bash
# Stop hook: auto-memory-suggest.sh
# OpenClaw-style auto-capture — анализирует сессию и предлагает что сохранить в memory
# Запускается при Stop (завершение ответа Claude)

set -euo pipefail

MEMORY_DIR="$HOME/.claude/projects/-Users-antonk/memory"
MEMORY_INDEX="$MEMORY_DIR/MEMORY.md"
SUGGEST_FILE="/tmp/claude-memory-suggest-$$"
CWD="$(pwd)"

# Определяем сессию по cwd
SESSION=""
case "$CWD" in
  */artvision-data*) SESSION="artvision-ops" ;;
  */artvision-tg-bot*) SESSION="artvision-bot" ;;
  */devops-agent*) SESSION="devops" ;;
  *) SESSION="unknown" ;;
esac

# Читаем stdin (Stop hook получает JSON)
INPUT=$(cat 2>/dev/null || echo '{}')

# Извлекаем transcript_path если есть
TRANSCRIPT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    # Stop hook может содержать session_id
    print(data.get('session_id', ''))
except:
    print('')
" 2>/dev/null || echo "")

# Собираем сигналы для memory-предложений из git diff (что изменилось в сессии)
SUGGESTIONS=""

# 1. Проверяем новые/изменённые файлы в memory-директории
MEMORY_CHANGES=$(cd "$MEMORY_DIR" 2>/dev/null && git diff --name-only HEAD 2>/dev/null | grep -c "memory/" 2>/dev/null || echo "0")

# 2. Проверяем изменённые клиентские файлы (новые решения?)
CLIENT_CHANGES=""
if [ -d "$CWD/clients" ]; then
    CLIENT_CHANGES=$(git diff --name-only 2>/dev/null | grep "^clients/" | head -5 || true)
fi

# 3. Проверяем изменения в rules/ (внутри текущего репо, если .claude/ в нём)
RULES_CHANGES=""
if [ -d "$CWD/.claude/rules" ]; then
    RULES_CHANGES=$(cd "$CWD" && git diff --name-only 2>/dev/null | grep "\.claude/rules/" | head -3 || true)
fi

# 4. Проверяем новые скрипты/хуки (внутри текущего репо)
SCRIPTS_CHANGES=""
if [ -d "$CWD/.claude/scripts" ] || [ -d "$CWD/.claude/hooks" ]; then
    SCRIPTS_CHANGES=$(cd "$CWD" && git diff --name-only 2>/dev/null | grep -E "\.claude/(scripts|hooks)/" | head -3 || true)
fi

# 5. Проверяем TODO.md изменения (новые задачи/решения?)
TODO_CHANGED="false"
for TODO_FILE in "$CWD/TODO.md" "$CWD/presale/TODO.md" "$CWD/products/TODO.md"; do
    if [ -f "$TODO_FILE" ] && git diff --name-only 2>/dev/null | grep -q "$(basename "$TODO_FILE")" 2>/dev/null; then
        TODO_CHANGED="true"
        break
    fi
done

# 6. Проверяем новые файлы в presale/ (новые клиенты?)
NEW_PRESALE=""
if [ -d "$CWD/presale" ]; then
    NEW_PRESALE=$(git ls-files --others --exclude-standard "presale/" 2>/dev/null | head -3 || true)
fi

# Собираем предложения
python3 - "$SESSION" "$CLIENT_CHANGES" "$RULES_CHANGES" "$SCRIPTS_CHANGES" "$TODO_CHANGED" "$NEW_PRESALE" << 'PYEOF'
import json, sys, os
from datetime import datetime

session = sys.argv[1]
client_changes = sys.argv[2].strip()
rules_changes = sys.argv[3].strip()
scripts_changes = sys.argv[4].strip()
todo_changed = sys.argv[5]
new_presale = sys.argv[6].strip()

suggestions = []

# Анализируем что произошло и предлагаем memory items
if client_changes:
    clients = set()
    for f in client_changes.split('\n'):
        parts = f.split('/')
        if len(parts) >= 2:
            clients.add(parts[1])
    for c in clients:
        suggestions.append(f"[project] Обновления клиента {c} — проверь context-log.md")

if rules_changes:
    suggestions.append(f"[feedback] Новые правила добавлены — убедись что они в MEMORY.md индексе")

if scripts_changes:
    for s in scripts_changes.split('\n'):
        if s:
            suggestions.append(f"[reference] Новый скрипт/хук: {os.path.basename(s)}")

if new_presale:
    suggestions.append("[project] Новые файлы в presale/ — возможно новый клиент, сохрани в clients-status.md")

if todo_changed == "true":
    suggestions.append("[project] TODO.md изменился — проверь не нужно ли обновить PROJECTS.md")

# Проверяем дату последнего обновления memory
memory_dir = os.path.expanduser("~/.claude/projects/-Users-antonk/memory")
memory_index = os.path.join(memory_dir, "MEMORY.md")
if os.path.exists(memory_index):
    mtime = os.path.getmtime(memory_index)
    days_old = (datetime.now().timestamp() - mtime) / 86400
    if days_old > 3:
        suggestions.append(f"[meta] MEMORY.md не обновлялся {int(days_old)} дней — пора актуализировать")

# Выводим результат
if suggestions:
    msg = "💾 AUTO-MEMORY: предложения для сохранения:\\n"
    for s in suggestions:
        msg += f"  • {s}\\n"
    msg += "Сохранить? (укажи номера или 'все')"
    # Выводим JSON для хука
    print(json.dumps({"systemMessage": msg}))
else:
    # Нет предложений — тихо выходим
    print("{}")

PYEOF
