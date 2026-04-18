#!/bin/bash
set -euo pipefail

# Asana Deadline Watchdog
# Проверяет:
# 1. Задачи с дедлайном через ≤24 часа → напомнить исполнителю
# 2. Задачи без дедлайна или без исполнителя → срочно Антону+Андрею
# 3. Просроченные задачи → алерт
#
# Запуск: cron каждые 6 часов (09:00, 15:00, 21:00, 03:00)
# Или вручную: ~/.claude/scripts/asana-deadline-watchdog.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOKENS_FILE="/Users/antonk/artvision-data/tokens.json"
LOG_FILE="/tmp/asana-watchdog-$(date +%Y%m%d).log"

# TG config
TG_BOT_TOKEN=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['telegram']['bot_token'])" 2>/dev/null || echo "")
TG_ANTON_ID=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['telegram']['admin_ids'][0])" 2>/dev/null || echo "")
TG_ANDREY_ID=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['telegram']['admin_ids'][1])" 2>/dev/null || echo "")

# Asana config
ASANA_PAT=$(python3 -c "import json; print(json.load(open('$TOKENS_FILE'))['asana']['pat'])" 2>/dev/null || echo "")
WORKSPACE_GID="1212305879398498"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

send_tg() {
    local chat_id="$1"
    local text="$2"
    if [ -n "$TG_BOT_TOKEN" ] && [ -n "$chat_id" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            -d chat_id="$chat_id" \
            -d text="$text" \
            -d parse_mode="HTML" > /dev/null 2>&1
    fi
}

send_to_team() {
    local text="$1"
    send_tg "$TG_ANTON_ID" "$text"
    send_tg "$TG_ANDREY_ID" "$text"
}

if [ -z "$ASANA_PAT" ]; then
    log "ERROR: ASANA_PAT not found in tokens.json"
    exit 1
fi

log "=== Watchdog run started ==="

# Fetch incomplete tasks with due dates
TASKS_JSON=$(curl -s -H "Authorization: Bearer $ASANA_PAT" \
    "https://app.asana.com/api/1.0/workspaces/$WORKSPACE_GID/tasks/search?completed=false&opt_fields=name,due_on,assignee,assignee.name,projects,projects.name&limit=100" 2>/dev/null || echo '{"data":[]}')

TODAY=$(date +%Y-%m-%d)
TOMORROW=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "+1 day" +%Y-%m-%d)

python3 << 'PYEOF'
import json
import sys
import os
from datetime import datetime, timedelta

tasks_json = os.environ.get("TASKS_JSON", '{"data":[]}')
today = os.environ.get("TODAY", "")
tomorrow = os.environ.get("TOMORROW", "")

try:
    data = json.loads(tasks_json)
    tasks = data.get("data", [])
except:
    tasks = []

overdue = []
due_soon = []  # within 24h
no_deadline = []
no_assignee = []

for t in tasks:
    name = t.get("name", "")
    due = t.get("due_on")
    assignee = t.get("assignee")
    projects = [p.get("name", "") for p in t.get("projects", [])]
    project_str = ", ".join(projects) if projects else "Без проекта"

    # Skip session tasks
    if name.startswith("[Session]"):
        continue

    assignee_name = assignee.get("name", "?") if assignee else None

    if not due:
        no_deadline.append(f"• {name} ({project_str})")

    if not assignee:
        no_assignee.append(f"• {name} ({project_str})" + (f" [до {due}]" if due else ""))

    if due:
        if due < today:
            overdue.append(f"• {name} — <b>просрочено {due}</b> ({assignee_name or '???'})")
        elif due <= tomorrow:
            due_soon.append(f"• {name} — <b>завтра {due}</b> ({assignee_name or '???'})")

# Build messages
messages = []

if overdue:
    msg = f"🔴 <b>ПРОСРОЧЕНО ({len(overdue)}):</b>\n" + "\n".join(overdue[:15])
    messages.append(("team", msg))

if due_soon:
    msg = f"🟠 <b>ДЕДЛАЙН ЗАВТРА ({len(due_soon)}):</b>\n" + "\n".join(due_soon[:15])
    messages.append(("team", msg))

if no_deadline:
    msg = f"⚪ <b>БЕЗ ДЕДЛАЙНА ({len(no_deadline)}):</b>\n" + "\n".join(no_deadline[:10])
    msg += "\n\n❓ Кто и когда? Проставьте дедлайн."
    messages.append(("team", msg))

if no_assignee:
    msg = f"👤 <b>БЕЗ ИСПОЛНИТЕЛЯ ({len(no_assignee)}):</b>\n" + "\n".join(no_assignee[:10])
    msg += "\n\n❓ Кто берёт? Назначьте исполнителя."
    messages.append(("team", msg))

# Output for bash
for target, msg in messages:
    print(f"MSG:{target}:{msg}")

if not messages:
    print("MSG:log:Все задачи в порядке — дедлайны проставлены, исполнители назначены.")

# Stats
print(f"STATS:overdue={len(overdue)},due_soon={len(due_soon)},no_deadline={len(no_deadline)},no_assignee={len(no_assignee)},total={len(tasks)}")
PYEOF
EXPORT TASKS_JSON TODAY TOMORROW

# Note: the python script above needs env vars passed differently
# Let me restructure

python3 - "$TASKS_JSON" "$TODAY" "$TOMORROW" << 'PYEOF' > /tmp/asana-watchdog-output.txt
import json
import sys

tasks_json = sys.argv[1] if len(sys.argv) > 1 else '{"data":[]}'
today = sys.argv[2] if len(sys.argv) > 2 else ""
tomorrow = sys.argv[3] if len(sys.argv) > 3 else ""

try:
    data = json.loads(tasks_json)
    tasks = data.get("data", [])
except:
    tasks = []

overdue = []
due_soon = []
no_deadline = []
no_assignee = []

for t in tasks:
    name = t.get("name", "")
    due = t.get("due_on")
    assignee = t.get("assignee")
    projects = [p.get("name", "") for p in t.get("projects", [])]
    project_str = ", ".join(projects) if projects else "Без проекта"

    if name.startswith("[Session]"):
        continue

    assignee_name = assignee.get("name", "?") if assignee else None

    if not due:
        no_deadline.append(f"  {name} ({project_str})")

    if not assignee:
        no_assignee.append(f"  {name} ({project_str})" + (f" [до {due}]" if due else ""))

    if due:
        if due < today:
            overdue.append(f"  {name} — просрочено {due} ({assignee_name or '???'})")
        elif due <= tomorrow:
            due_soon.append(f"  {name} — завтра {due} ({assignee_name or '???'})")

if overdue:
    print(f"OVERDUE:{len(overdue)}")
    for o in overdue[:15]:
        print(o)
if due_soon:
    print(f"DUE_SOON:{len(due_soon)}")
    for d in due_soon[:15]:
        print(d)
if no_deadline:
    print(f"NO_DEADLINE:{len(no_deadline)}")
    for n in no_deadline[:10]:
        print(n)
if no_assignee:
    print(f"NO_ASSIGNEE:{len(no_assignee)}")
    for n in no_assignee[:10]:
        print(n)
if not (overdue or due_soon or no_deadline or no_assignee):
    print("ALL_OK")

print(f"TOTAL:{len(tasks)}")
PYEOF

# Parse output and send TG messages
OUTPUT=$(cat /tmp/asana-watchdog-output.txt 2>/dev/null || echo "ERROR")

ALERT_MSG="🤖 <b>Asana Watchdog</b> — $(date '+%d.%m %H:%M')\n\n"
HAS_ALERTS=false

if echo "$OUTPUT" | grep -q "^OVERDUE:"; then
    COUNT=$(echo "$OUTPUT" | grep "^OVERDUE:" | cut -d: -f2)
    ITEMS=$(echo "$OUTPUT" | grep -A 100 "^OVERDUE:" | tail -n +2 | head -"$COUNT")
    ALERT_MSG+="🔴 <b>ПРОСРОЧЕНО ($COUNT):</b>\n$ITEMS\n\n"
    HAS_ALERTS=true
fi

if echo "$OUTPUT" | grep -q "^DUE_SOON:"; then
    COUNT=$(echo "$OUTPUT" | grep "^DUE_SOON:" | cut -d: -f2)
    ITEMS=$(echo "$OUTPUT" | grep -A 100 "^DUE_SOON:" | tail -n +2 | head -"$COUNT")
    ALERT_MSG+="🟠 <b>ДЕДЛАЙН ЗАВТРА ($COUNT):</b>\n$ITEMS\n\n"
    HAS_ALERTS=true
fi

if echo "$OUTPUT" | grep -q "^NO_DEADLINE:"; then
    COUNT=$(echo "$OUTPUT" | grep "^NO_DEADLINE:" | cut -d: -f2)
    ITEMS=$(echo "$OUTPUT" | grep -A 100 "^NO_DEADLINE:" | tail -n +2 | head -"$COUNT")
    ALERT_MSG+="⚪ <b>БЕЗ ДЕДЛАЙНА ($COUNT):</b>\n$ITEMS\n\n❓ Кто и когда?\n\n"
    HAS_ALERTS=true
fi

if echo "$OUTPUT" | grep -q "^NO_ASSIGNEE:"; then
    COUNT=$(echo "$OUTPUT" | grep "^NO_ASSIGNEE:" | cut -d: -f2)
    ITEMS=$(echo "$OUTPUT" | grep -A 100 "^NO_ASSIGNEE:" | tail -n +2 | head -"$COUNT")
    ALERT_MSG+="👤 <b>БЕЗ ИСПОЛНИТЕЛЯ ($COUNT):</b>\n$ITEMS\n\n❓ Кто берёт?\n\n"
    HAS_ALERTS=true
fi

if [ "$HAS_ALERTS" = true ]; then
    send_to_team "$ALERT_MSG"
    log "Sent alerts to team"
else
    log "All tasks OK — no alerts needed"
fi

log "=== Watchdog run completed ==="
