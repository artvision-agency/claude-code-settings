#!/bin/bash
# SessionStart: быстрая проверка просроченных задач в Asana
# Только вывод в session — без TG-уведомлений

TOKENS_FILE="/Users/antonk/artvision-data/tokens.json"
ASANA_PAT=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['asana']['pat'])" 2>/dev/null || exit 0)

[ -z "$ASANA_PAT" ] && exit 0

WORKSPACE="1212305879398498"
TODAY=$(date +%Y-%m-%d)

# Найти просроченные задачи (due_on < today, не completed)
OVERDUE=$(curl -s -H "Authorization: Bearer $ASANA_PAT" \
  "https://app.asana.com/api/1.0/tasks?workspace=$WORKSPACE&completed_since=now&opt_fields=name,due_on,assignee.name&limit=50" 2>/dev/null \
  | python3 -c "
import json, sys, datetime
try:
    data = json.load(sys.stdin).get('data', [])
    today = datetime.date.today()
    overdue = []
    no_deadline = []
    for t in data:
        due = t.get('due_on')
        name = t.get('name', '?')[:50]
        assignee = (t.get('assignee') or {}).get('name', '?')
        if due:
            if datetime.date.fromisoformat(due) < today:
                overdue.append(f'  - {name} (due {due}, {assignee})')
        else:
            no_deadline.append(f'  - {name} ({assignee})')
    if overdue:
        print(f'Просроченных: {len(overdue)}')
        print('\n'.join(overdue[:5]))
    if no_deadline and len(no_deadline) > 3:
        print(f'Без дедлайна: {len(no_deadline)} задач')
except:
    pass
" 2>/dev/null)

if [ -n "$OVERDUE" ]; then
  echo "⚠️ ASANA:"
  echo "$OVERDUE"
fi

exit 0
