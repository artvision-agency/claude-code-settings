#!/usr/bin/env bash
# asana-overdue-cache.sh — обновляет ~/.claude/state/asana-overdue.cache
# для отображения в session-menu. Запускается LaunchAgent'ом раз в 30 мин.
#
# Формат кэша: первая строка — число, далее до 5 строк "name|due|assignee".
# При ошибке/отсутствии токена — оставляет старый кэш нетронутым.

set -Eeuo pipefail

readonly TOKENS="${HOME}/artvision-data/tokens.json"
readonly CACHE_DIR="${HOME}/.claude/state"
readonly CACHE="${CACHE_DIR}/asana-overdue.cache"
readonly WORKSPACE="1212305879398498"

mkdir -p "$CACHE_DIR"

[[ -f "$TOKENS" ]] || exit 0
PAT=$(python3 -c "import json; print(json.load(open('$TOKENS'))['asana']['pat'])" 2>/dev/null) || exit 0
[[ -n "$PAT" ]] || exit 0

RESP=$(curl -sS --max-time 15 \
  -H "Authorization: Bearer $PAT" \
  "https://app.asana.com/api/1.0/tasks?workspace=${WORKSPACE}&completed_since=now&opt_fields=name,due_on,assignee.name&limit=100" 2>/dev/null) || exit 0

python3 - "$CACHE" <<PY
import json, sys, datetime
cache_path = sys.argv[1]
try:
    data = json.loads('''$RESP''').get('data', [])
except Exception:
    sys.exit(0)
today = datetime.date.today()
overdue = []
for t in data:
    due = t.get('due_on')
    if not due:
        continue
    try:
        if datetime.date.fromisoformat(due) < today:
            name = (t.get('name') or '?')[:60]
            assignee = ((t.get('assignee') or {}).get('name') or '?')
            overdue.append(f"{name}|{due}|{assignee}")
    except Exception:
        continue
overdue.sort()
with open(cache_path, 'w') as f:
    f.write(f"{len(overdue)}\n")
    for line in overdue[:5]:
        f.write(line + "\n")
PY
