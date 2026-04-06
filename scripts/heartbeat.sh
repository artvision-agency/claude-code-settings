#!/bin/bash
set -euo pipefail

# ============================================================
# Artvision Heartbeat — проактивный мониторинг и алерты в TG
# Вдохновлено OpenClaw heartbeats
# Запуск: каждые 4 часа через LaunchAgent
# ============================================================

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

TOKENS_FILE="/Users/antonk/artvision-data/tokens.json"
SCHEDULE_FILE="/Users/antonk/artvision-data/schedule/reports-invoices.json"
DATA_DIR="/Users/antonk/artvision-data"
CLIENTS_DIR="${DATA_DIR}/clients"
LOG_FILE="/tmp/heartbeat-$(date +%Y%m%d).log"
MAX_RETRIES=2

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

# ---- Extract tokens via python3 (safe: vars via sys.argv, not heredoc) ----
read_token() {
  local key_path="$1"
  python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
keys = sys.argv[2].split('.')
obj = d
for k in keys:
    obj = obj[k]
print(obj)
" "$TOKENS_FILE" "$key_path"
}

BOT_TOKEN=$(read_token "telegram.portal_bot.token")
CHAT_ID=$(read_token "telegram.admin_ids.0" 2>/dev/null || python3 -c "
import json
with open('$TOKENS_FILE') as f:
    d = json.load(f)
print(d['telegram']['admin_ids'][0])
")

NOW=$(date "+%H:%M %d.%m.%Y")
TODAY=$(date "+%Y-%m-%d")

# ============================================================
# 1. Просроченные задачи в TODO.md
# ============================================================
check_overdue_todos() {
  local overdue_count=0
  local overdue_list=""

  for todo_file in "${TODO_FILES[@]}"; do
    [ -f "$todo_file" ] || continue

    while IFS= read -r line; do
      if printf '%s' "$line" | grep -qoE '[0-9]{4}-[0-9]{2}-[0-9]{2}'; then
        task_date=$(printf '%s' "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
        if [[ "$task_date" < "$TODAY" ]]; then
          overdue_count=$((overdue_count + 1))
          task_text=$(printf '%s' "$line" | sed 's/^[[:space:]]*- \[ \] //' | head -c 80)
          overdue_list="${overdue_list}
  • ${task_text}"
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

  local active_clients
  active_clients=$(python3 << 'PYEOF'
import json
with open("/Users/antonk/artvision-data/schedule/reports-invoices.json") as f:
    d = json.load(f)
for name, info in d.get("reports_and_invoices", {}).items():
    mode = info.get("mode", "")
    if mode == "kp":
        continue
    if info.get("report_day") or info.get("invoice_day") or info.get("weekly_report"):
        print(name)
PYEOF
  )

  for client in $active_clients; do
    client_dir=""
    for candidate in "${CLIENTS_DIR}/${client}" "${CLIENTS_DIR}/${client//-/}"; do
      if [ -d "$candidate" ]; then
        client_dir="$candidate"
        break
      fi
    done

    if [ -z "$client_dir" ]; then
      client_dir=$(find "$CLIENTS_DIR" -maxdepth 1 -type d -name "*${client%%-*}*" 2>/dev/null | head -1)
    fi

    if [ -n "$client_dir" ] && [ -d "$client_dir" ]; then
      last_commit_date=$(cd "$DATA_DIR" && git log -1 --format="%ct" -- "clients/$(basename "$client_dir")/" 2>/dev/null || echo "0")

      if [ "$last_commit_date" -lt "$threshold_ts" ] 2>/dev/null; then
        no_touch_count=$((no_touch_count + 1))
        days_ago=$(( ($(date "+%s") - last_commit_date) / 86400 ))
        no_touch="${no_touch}
  • ${client} (${days_ago}д)"
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
      details="${details}
  • ${repo_name}: ${count} файлов"
    fi
  done

  echo "${total}|${details}"
}

# ============================================================
# 4. Счета и отчёты сегодня/завтра (quoted heredoc — no injection)
# ============================================================
check_schedule() {
  python3 << 'PYEOF'
import json
from datetime import datetime, timedelta

today = int(datetime.now().strftime("%-d"))
tomorrow = int((datetime.now() + timedelta(days=1)).strftime("%-d"))

with open("/Users/antonk/artvision-data/schedule/reports-invoices.json") as f:
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

# Collect data (trap errors — don't let set -e kill the whole script)
overdue_result=$(check_overdue_todos || echo "0|")
overdue_count=$(printf '%s' "$overdue_result" | head -1 | cut -d'|' -f1)
overdue_list=$(printf '%s' "$overdue_result" | cut -d'|' -f2-)

touch_result=$(check_client_touchpoints || echo "0|")
touch_count=$(printf '%s' "$touch_result" | head -1 | cut -d'|' -f1)
touch_list=$(printf '%s' "$touch_result" | cut -d'|' -f2-)

uncommit_result=$(check_uncommitted || echo "0|")
uncommit_count=$(printf '%s' "$uncommit_result" | head -1 | cut -d'|' -f1)
uncommit_list=$(printf '%s' "$uncommit_result" | cut -d'|' -f2-)

schedule_result=$(check_schedule || echo "0|")
schedule_count=$(printf '%s' "$schedule_result" | head -1 | cut -d'|' -f1)
schedule_list=$(printf '%s' "$schedule_result" | cut -d'|' -f2-)

revenue_pulse=$(check_revenue_pulse || echo "N/A")

# Build message using printf (portable, no echo -e)
MSG=$(printf '%s\n' "💓 HEARTBEAT — ${NOW}" "━━━━━━━━━━━━━━━━━━━━")

has_issues=false

if [ "$overdue_count" -gt 0 ] 2>/dev/null; then
  MSG=$(printf '%s\n%s%s' "$MSG" "🔴 Просрочено: ${overdue_count} задач" "$overdue_list")
  has_issues=true
fi

if [ "$touch_count" -gt 0 ] 2>/dev/null; then
  MSG=$(printf '%s\n%s%s' "$MSG" "📞 Без контакта >7д: ${touch_count}" "$touch_list")
  has_issues=true
fi

if [ "$schedule_count" -gt 0 ] 2>/dev/null; then
  MSG=$(printf '%s\n%s\n%s' "$MSG" "💰 Счета/отчёты:" "$schedule_list")
  has_issues=true
fi

if [ "$uncommit_count" -gt 0 ] 2>/dev/null; then
  MSG=$(printf '%s\n%s%s' "$MSG" "📝 Незакоммичено: ${uncommit_count} файлов" "$uncommit_list")
  has_issues=true
fi

MSG=$(printf '%s\n%s\n%s' "$MSG" "━━━━━━━━━━━━━━━━━━━━" "📊 Клиенты: ${revenue_pulse}")

if [ "$has_issues" = false ]; then
  MSG=$(printf '%s\n%s' "$MSG" "✅ Всё чисто — нет проблем")
fi

# Send to Telegram with --data-urlencode (safe for special chars) + timeout + retry
send_tg() {
  curl -s --max-time 30 -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${MSG}" \
    -d "parse_mode=" \
    2>&1
}

send_result=""
for attempt in $(seq 1 $MAX_RETRIES); do
  send_result=$(send_tg) || true
  if printf '%s' "$send_result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)" 2>/dev/null; then
    echo "[$(date)] Heartbeat sent OK. overdue=${overdue_count} touch=${touch_count} uncommit=${uncommit_count} schedule=${schedule_count}" >> "$LOG_FILE"
    echo "OK"
    exit 0
  fi
  [ "$attempt" -lt "$MAX_RETRIES" ] && sleep 3
done

echo "[$(date)] FAILED after ${MAX_RETRIES} attempts: $send_result" >> "$LOG_FILE"
exit 1
