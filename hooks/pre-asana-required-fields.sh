#!/bin/bash
# PreToolUse hook: блокирует создание задачи в Asana без обязательных полей
# Matcher: mcp__asana__asana_create_task
#
# Проверяет: assignee, due_on, project_id
# Если что-то пустое — возвращает блокирующее сообщение

set -euo pipefail

# Читаем JSON из stdin (tool input)
INPUT=$(cat)

# Извлекаем поля
ASSIGNEE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('assignee',''))" 2>/dev/null || echo "")
DUE_ON=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('due_on',''))" 2>/dev/null || echo "")
PROJECT_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('project_id',''))" 2>/dev/null || echo "")

MISSING=""

if [ -z "$ASSIGNEE" ]; then
    MISSING="${MISSING}\n- [ ] Ответственный (assignee) — кто делает?"
fi

if [ -z "$DUE_ON" ]; then
    MISSING="${MISSING}\n- [ ] Дедлайн (due_on) — до какого числа? (YYYY-MM-DD)"
fi

if [ -z "$PROJECT_ID" ]; then
    MISSING="${MISSING}\n- [ ] Проект (project_id) — в какой проект?"
fi

if [ -n "$MISSING" ]; then
    echo "❌ БЛОК: Asana задача без обязательных полей!"
    echo ""
    echo "Не хватает:"
    echo -e "$MISSING"
    echo ""
    echo "СПРОСИ у постановщика. НЕ выдумывай значения."
    echo "Правило: ~/.claude/rules/asana-required-fields.md"
    exit 2
fi

exit 0
