#!/bin/bash
set -euo pipefail

# ============================================================
# Artvision Heartbeat — проактивный мониторинг и алерты в TG
# Вдохновлено OpenClaw heartbeats
# Запуск: каждые 4 часа через LaunchAgent
# ============================================================

TOKENS_FILE="/Users/antonk/artvision-data/tokens.json"
SCHEDULE_FILE="/Users/antonk/artvision-data/schedule/reports-invoices.json"
DATA_DIR="/Users/antonk/artvision-data"
CLIENTS_DIR="${DATA_DIR}/clients"
LOG_FILE="/tmp/heartbeat-$(date +%Y%m%d).log"

# Repos to check for uncommitted changes
REPOS=(
  "/Users/antonk/artvision-data"
  "/Users/antonk/artvision-tg-bot"
  "/Users/antonk/devops-agent"
)

# TODO files to check for overdue tasks
TODO_FILES=(
  "${DATA_DIR}/TODO.md"
  "${DATA_DIR}/presale/TODO.md"
  "${DATA_DIR}/products/TODO.md"
)

# ---- Extract tokens via python3 (safe for JSON) ----
read_token() {
  local key_path="$1"
  python3 << PYEOF
import json
with open("${TOKENS_FILE}") as f:
    d = json.load(f)
keys = "${key_path}".split(".")
obj = d
for k in keys:
    obj = obj[k]
print(obj)
PYEOF
}

BOT_TOKEN=$(read_token "telegram.portal_bot.token")
CHAT_ID=$(python3 << 'PYEOF'
import json
with open("/Users/antonk/artvision-data/tokens.json") as f:
    d = json.load(f)
# Anton's chat_id from admin_ids
print(d["telegram"]["admin_ids"][0])
PYEOF
)

NOW=$(date "+%H:%M %d.%m.%Y")
TODAY=$(date "+%Y-%m-%d")
TODAY_DAY=$(date "+%-d")  # day of month without leading zero

# ============================================================
# 1. Просроченные задачи в TODO.md
# ============================================================
check_overdue_todos() {
  local overdue_count=0
  local overdue_list=""

  for todo_file in "${TODO_FILES[@]}"; do
    [ -f "$todo_file" ] || continue

    # Find unchecked tasks with dates in the past
    # Pattern: - [ ] ... (YYYY-MM-DD) or ... дедлайн YYYY-MM-DD or ... до DD.MM
    while IFS= read -r line; do
      # Extract ISO date (YYYY-MM-DD) from line
      if echo "$line" | grep -qoE '[0-9]{4}-[0-9]{2}-[0-9]{2}'; then
        task_date=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
        if [[ "$task_date" < "$TODAY" ]]; then
          overdue_count=$((overdue_count + 1))
          # Clean up task text for message
          task_text=$(echo "$line" | sed 's/^[[:space:]]*- \[ \] //' | head -c 80)
          overdue_list="${overdue_list}\n  • ${task_text}"
        fi
      fi
    done < <(grep -E '^\s*- \[ \]' "$todo_file" 2>/dev/null || true)
  done

  echo "${overdue_count}|${overdue_list}"
}

# ============================================================
# 2. Клиенты без touchpoint >7 дней
# ============================================================
check_client_touchpoints() {
  local no_touch=""
  local no_touch_count=0
  local threshold_ts
  threshold_ts=$(date -v-7d "+%s" 2>/dev/null || date -d "7 days ago" "+%s" 2>/dev/null || echo 0)

  # Active clients from schedule (have report_day or invoice_day set)
  local active_clients
  active_clients=$(python3 << 'PYEOF'
import json
with open("/Users/antonk/artvision-data/schedule/reports-invoices.json") as f:
    d = json.load(f)
for name, info in d.get("reports_and_invoices", {}).items():
    mode = info.get("mode", "")
    if mode == "kp":
        continue
    # Only check clients with active schedules
    if info.get("report_day") or info.get("invoice_day") or info.get("weekly_report"):
        print(name)
PYEOF
  )

  for client in $active_clients; do
    # Map schedule name to clients/ folder
    client_dir=""
    for candidate in "${CLIENTS_DIR}/${client}" "${CLIENTS_DIR}/${client//-/}"; do
      if [ -d "$candidate" ]; then
        client_dir="$candidate"
        break
      fi
    done

    if [ -z "$client_dir" ]; then
      # Try finding by partial match
      client_dir=$(find "$CLIENTS_DIR" -maxdepth 1 -type d -name "*${client%%-*}*" 2>/dev/null | head -1)
    fi

    if [ -n "$client_dir" ] && [ -d "$client_dir" ]; then
      # Last git commit touching this client
      last_commit_date=$(cd "$DATA_DIR" && git log -1 --format="%ct" -- "clients/$(basename "$client_dir")/" 2>/dev/null || echo "0")

      if [ "$last_commit_date" -lt "$threshold_ts" ] 2>/dev/null; then
        no_touch_count=$((no_touch_count + 1))
        days_ago=$(( ($(date "+%s") - last_commit_date) / 86400 ))
        no_touch="${no_touch}\n  • ${client} (${days_ago}д)"
      fi
    fi
  done

  echo "${no_touch_count}|${no_touch}"
}

# ============================================================
# 3. Незакоммиченные изменения
# ============================================================
check_uncommitted() {
  local total=0
  local details=""

  for repo in "${REPOS[@]}"; do
    [ -d "$repo/.git" ] || continue
    repo_name=$(basename "$repo")
    count=$(cd "$repo" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
      total=$((total + count))
      details="${details}\n  • ${repo_name}: ${count} файлов"
    fi
  done

  echo "${total}|${details}"
}

# ============================================================
# 4. Счета и отчёты сегодня/завтра
# ============================================================
check_schedule() {
  python3 << PYEOF
import json
from datetime import datetime

today = int(datetime.now().strftime("%-d"))
tomorrow = today + 1 if today < 28 else 1

with open("${SCHEDULE_FILE}") as f:
    d = json.load(f)

items = []
for name, info in d.get("reports_and_invoices", {}).items():
    inv_day = info.get("invoice_day")
    inv_days = info.get("invoice_days", [])
    rep_day = info.get("report_day")
    mode = info.get("mode", "")

    all_inv_days = inv_days if inv_days else ([inv_day] if inv_day else [])

    for day in all_inv_days:
        if day == today:
            label = "KП" if mode == "kp" else "Счёт"
            items.append(f"  {label} {name} (сегодня)")
        elif day == tomorrow:
            label = "KП" if mode == "kp" else "Счёт"
            items.append(f"  {label} {name} (завтра)")

    if rep_day == today:
        items.append(f"  Отчёт {name} (сегодня)")
    elif rep_day == tomorrow:
        items.append(f"  Отчёт {name} (завтра)")

# Personal payments
for name, info in d.get("personal_payments", {}).items():
    rem_day = info.get("reminder_day")
    dead_day = info.get("deadline_day")
    if rem_day == today:
        items.append(f"  Напоминание: {info.get('name', name)} (дедлайн {dead_day}-го)")
    elif dead_day == today:
        items.append(f"  ДЕДЛАЙН: {info.get('name', name)}")

if items:
    print(str(len(items)) + "|" + "\n".join(items))
else:
    print("0|")
PYEOF
}

# ============================================================
# 5. Revenue pulse — краткая сводка
# ============================================================
check_revenue_pulse() {
  # Count active clients from schedule
  python3 << 'PYEOF'
import json
with open("/Users/antonk/artvision-data/schedule/reports-invoices.json") as f:
    d = json.load(f)
active = 0
kp = 0
for name, info in d.get("reports_and_invoices", {}).items():
    mode = info.get("mode", "")
    if mode == "kp":
        kp += 1
    elif info.get("report_day") or info.get("invoice_day") or info.get("weekly_report"):
        active += 1
print(f"{active} активных, {kp} в presale")
PYEOF
}

# ============================================================
# Сборка и отправка сообщения
# ============================================================

# Collect data
overdue_result=$(check_overdue_todos)
overdue_count=$(echo "$overdue_result" | cut -d'|' -f1)
overdue_list=$(echo "$overdue_result" | cut -d'|' -f2-)

touch_result=$(check_client_touchpoints)
touch_count=$(echo "$touch_result" | cut -d'|' -f1)
touch_list=$(echo "$touch_result" | cut -d'|' -f2-)

uncommit_result=$(check_uncommitted)
uncommit_count=$(echo "$uncommit_result" | cut -d'|' -f1)
uncommit_list=$(echo "$uncommit_result" | cut -d'|' -f2-)

schedule_result=$(check_schedule)
schedule_count=$(echo "$schedule_result" | cut -d'|' -f1)
schedule_list=$(echo "$schedule_result" | cut -d'|' -f2-)

revenue_pulse=$(check_revenue_pulse)

# Build message
MSG="💓 HEARTBEAT — ${NOW}
━━━━━━━━━━━━━━━━━━━━"

# Only show sections with issues (or all if nothing)
has_issues=false

if [ "$overdue_count" -gt 0 ]; then
  MSG="${MSG}
🔴 Просрочено: ${overdue_count} задач$(echo -e "$overdue_list")"
  has_issues=true
fi

if [ "$touch_count" -gt 0 ]; then
  MSG="${MSG}
📞 Без контакта >7д: ${touch_count}$(echo -e "$touch_list")"
  has_issues=true
fi

if [ "$schedule_count" -gt 0 ]; then
  MSG="${MSG}
💰 Счета/отчёты:
$(echo -e "$schedule_list")"
  has_issues=true
fi

if [ "$uncommit_count" -gt 0 ]; then
  MSG="${MSG}
📝 Незакоммичено: ${uncommit_count} файлов$(echo -e "$uncommit_list")"
  has_issues=true
fi

MSG="${MSG}
━━━━━━━━━━━━━━━━━━━━
📊 Клиенты: ${revenue_pulse}"

if [ "$has_issues" = false ]; then
  MSG="${MSG}
✅ Всё чисто — нет проблем"
fi

# Send to Telegram
send_result=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=${MSG}" \
  -d "parse_mode=" \
  2>&1)

# Log
echo "[$(date)] Heartbeat sent. overdue=${overdue_count} touch=${touch_count} uncommit=${uncommit_count} schedule=${schedule_count}" >> "$LOG_FILE"

# Check if send succeeded
if echo "$send_result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)" 2>/dev/null; then
  echo "OK"
else
  echo "FAILED: $send_result" >> "$LOG_FILE"
  exit 1
fi
