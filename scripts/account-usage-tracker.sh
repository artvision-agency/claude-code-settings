#!/bin/bash
# Account Usage Tracker — отслеживает расход по аккаунтам Claude Max
# Записывает стоимость каждой сессии, считает недельный итог
# При приближении к лимиту (97%) — алерт + инструкция переключения
set -euo pipefail

USAGE_FILE="$HOME/.claude/account-usage.json"
WEEKLY_LIMIT_USD=150  # Оценочный лимит Max подписки в $ за неделю (корректировать по факту)
ALERT_THRESHOLD=97    # % от лимита для алерта

# Аккаунты
ACCOUNT_1="justtrance@gmail.com"
ACCOUNT_2="adw.artvision.pro@gmail.com"

# Текущий аккаунт
get_current_account() {
    claude auth status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('email','unknown'))" 2>/dev/null || echo "unknown"
}

# Инициализация файла
init_usage_file() {
    if [ ! -f "$USAGE_FILE" ]; then
        python3 << 'PYEOF'
import json
from datetime import datetime
data = {
    "week_start": datetime.now().strftime("%Y-%m-%d"),
    "accounts": {
        "justtrance@gmail.com": {"weekly_cost": 0.0, "sessions": []},
        "adw.artvision.pro@gmail.com": {"weekly_cost": 0.0, "sessions": []}
    },
    "weekly_limit_usd": 150,
    "alert_threshold_pct": 97
}
with open("$HOME/.claude/account-usage.json".replace("$HOME", __import__("os").environ["HOME"]), "w") as f:
    json.dump(data, f, indent=2)
PYEOF
    fi
}

# Записать стоимость сессии
log_session_cost() {
    local account="$1"
    local cost="$2"

    python3 << PYEOF
import json, os
from datetime import datetime, timedelta

fpath = os.path.expanduser("~/.claude/account-usage.json")
with open(fpath) as f:
    data = json.load(f)

# Проверить — новая неделя? (сброс в понедельник 03:00 MSK)
week_start = datetime.strptime(data["week_start"], "%Y-%m-%d")
now = datetime.now()
days_diff = (now - week_start).days
if days_diff >= 7:
    data["week_start"] = now.strftime("%Y-%m-%d")
    for acc in data["accounts"]:
        data["accounts"][acc]["weekly_cost"] = 0.0
        data["accounts"][acc]["sessions"] = []

# Добавить сессию
account = "$account"
cost = float("$cost")
if account in data["accounts"]:
    data["accounts"][account]["weekly_cost"] += cost
    data["accounts"][account]["sessions"].append({
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "cost": cost
    })

with open(fpath, "w") as f:
    json.dump(data, f, indent=2)

# Вывод текущего состояния
for acc, info in data["accounts"].items():
    pct = (info["weekly_cost"] / data["weekly_limit_usd"]) * 100
    marker = " <-- CURRENT" if acc == account else ""
    print(f"  {acc}: \${info['weekly_cost']:.2f} ({pct:.0f}%){marker}")
PYEOF
}

# Проверить — пора переключаться?
check_and_alert() {
    python3 << 'PYEOF'
import json, os, sys

fpath = os.path.expanduser("~/.claude/account-usage.json")
if not os.path.exists(fpath):
    sys.exit(0)

with open(fpath) as f:
    data = json.load(f)

limit = data.get("weekly_limit_usd", 150)
threshold = data.get("alert_threshold_pct", 97)

# Текущий аккаунт
import subprocess
try:
    result = subprocess.run(["claude", "auth", "status", "--json"], capture_output=True, text=True, timeout=5)
    current = json.loads(result.stdout).get("email", "unknown")
except:
    current = "unknown"

accounts = data.get("accounts", {})
current_info = accounts.get(current, {})
current_cost = current_info.get("weekly_cost", 0)
current_pct = (current_cost / limit) * 100 if limit > 0 else 0

if current_pct >= threshold:
    # Найти альтернативный аккаунт с меньшим расходом
    other = None
    other_pct = 100
    for acc, info in accounts.items():
        if acc != current:
            pct = (info.get("weekly_cost", 0) / limit) * 100
            if pct < other_pct:
                other = acc
                other_pct = pct

    if other and other_pct < threshold:
        print(f"SWITCH_NEEDED|{current}|{other}|{current_pct:.0f}|{other_pct:.0f}")
    else:
        print(f"BOTH_EXHAUSTED|{current_pct:.0f}|{other_pct:.0f}")
else:
    print(f"OK|{current}|{current_pct:.0f}")
PYEOF
}

# Переключить аккаунт
switch_account() {
    local target_email="$1"
    echo "Переключение на $target_email..."
    echo "Выполни в НОВОМ терминале:"
    echo ""
    echo "  claude auth logout && claude auth login --email $target_email"
    echo ""
    echo "Затем открой новую сессию Claude Code."
}

# Статус
show_status() {
    init_usage_file
    echo "=== Claude Max Account Usage ==="
    python3 << 'PYEOF'
import json, os
fpath = os.path.expanduser("~/.claude/account-usage.json")
with open(fpath) as f:
    data = json.load(f)
limit = data.get("weekly_limit_usd", 150)
print(f"Week started: {data['week_start']} | Limit: ${limit}/week | Alert: {data['alert_threshold_pct']}%")
print()
for acc, info in data["accounts"].items():
    cost = info.get("weekly_cost", 0)
    pct = (cost / limit) * 100 if limit > 0 else 0
    sessions = len(info.get("sessions", []))
    bar_len = int(pct / 5)
    bar = "#" * bar_len + "-" * (20 - bar_len)
    status = "LIMIT!" if pct >= 97 else "OK"
    print(f"  {acc}")
    print(f"    [{bar}] ${cost:.2f} ({pct:.0f}%) | {sessions} sessions | {status}")
PYEOF
}

# CLI
case "${1:-status}" in
    log)    init_usage_file; log_session_cost "${2:-unknown}" "${3:-0}" ;;
    check)  init_usage_file; check_and_alert ;;
    switch) switch_account "${2:-}" ;;
    status) show_status ;;
    init)   init_usage_file; echo "Initialized $USAGE_FILE" ;;
    *)      echo "Usage: $0 {status|log|check|switch|init}" ;;
esac
