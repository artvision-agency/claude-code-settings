#!/bin/bash
# Account Usage Tracker — Claude Max (подписка)
# Считает СЕССИИ и TURNS (не доллары — Max = подписка)
# Лимит: ~900 msgs / 5h window (rolling) на аккаунт
set -euo pipefail

USAGE_FILE="$HOME/.claude/account-usage.json"
WEEKLY_SESSION_LIMIT=500  # Оценочный лимит сессий в неделю на аккаунт
ALERT_THRESHOLD=95        # % от лимита для алерта (за 5% до конца → предложить переключение)

# Инициализация файла
init_usage_file() {
    if [ ! -f "$USAGE_FILE" ]; then
        python3 << 'PYEOF'
import json, os
from datetime import datetime
data = {
    "week_start": datetime.now().strftime("%Y-%m-%d"),
    "weekly_session_limit": 500,
    "alert_threshold_pct": 85,
    "accounts": {
        "justtrance@gmail.com": {"weekly_sessions": 0, "weekly_turns": 0, "sessions": []},
        "adw.artvision.pro@gmail.com": {"weekly_sessions": 0, "weekly_turns": 0, "sessions": []}
    }
}
fpath = os.path.expanduser("~/.claude/account-usage.json")
with open(fpath, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
    fi
}

# Записать сессию
log_session() {
    local account="$1"
    local turns="${2:-1}"

    python3 << PYEOF
import json, os
from datetime import datetime

fpath = os.path.expanduser("~/.claude/account-usage.json")
with open(fpath) as f:
    data = json.load(f)

# Миграция старого формата
for acc in data.get("accounts", {}):
    info = data["accounts"][acc]
    if "weekly_cost" in info:
        del info["weekly_cost"]
    if "weekly_sessions" not in info:
        info["weekly_sessions"] = len(info.get("sessions", []))
    if "weekly_turns" not in info:
        info["weekly_turns"] = 0

if "weekly_limit_usd" in data:
    del data["weekly_limit_usd"]
if "weekly_session_limit" not in data:
    data["weekly_session_limit"] = 500

# Проверить — новая неделя? (сброс по понедельникам)
week_start = datetime.strptime(data["week_start"], "%Y-%m-%d")
now = datetime.now()
days_diff = (now - week_start).days
if days_diff >= 7:
    data["week_start"] = now.strftime("%Y-%m-%d")
    for acc in data["accounts"]:
        data["accounts"][acc]["weekly_sessions"] = 0
        data["accounts"][acc]["weekly_turns"] = 0
        data["accounts"][acc]["sessions"] = []

# Добавить сессию
account = "$account"
turns = int("$turns")
if account in data["accounts"]:
    data["accounts"][account]["weekly_sessions"] += 1
    data["accounts"][account]["weekly_turns"] += turns
    # Хранить последние 50 сессий (не раздувать файл)
    sessions = data["accounts"][account]["sessions"]
    sessions.append({
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "turns": turns
    })
    if len(sessions) > 50:
        data["accounts"][account]["sessions"] = sessions[-50:]

with open(fpath, "w") as f:
    json.dump(data, f, indent=2)

# Вывод
for acc, info in data["accounts"].items():
    s = info.get("weekly_sessions", 0)
    t = info.get("weekly_turns", 0)
    marker = " <-- CURRENT" if acc == account else ""
    print(f"  {acc}: {s} sessions, {t} turns{marker}")
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

limit = data.get("weekly_session_limit", 500)
threshold = data.get("alert_threshold_pct", 85)

# Текущий аккаунт
import subprocess
try:
    result = subprocess.run(["claude", "auth", "status", "--json"], capture_output=True, text=True, timeout=5)
    current = json.loads(result.stdout).get("email", "unknown")
except:
    current = "unknown"

accounts = data.get("accounts", {})
current_info = accounts.get(current, {})
current_sessions = current_info.get("weekly_sessions", 0)
current_pct = (current_sessions / limit) * 100 if limit > 0 else 0

if current_pct >= threshold:
    other = None
    other_pct = 100
    for acc, info in accounts.items():
        if acc != current:
            pct = (info.get("weekly_sessions", 0) / limit) * 100
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

# Статус
show_status() {
    init_usage_file
    echo "=== Claude Max Account Usage ==="
    python3 << 'PYEOF'
import json, os
fpath = os.path.expanduser("~/.claude/account-usage.json")
with open(fpath) as f:
    data = json.load(f)
limit = data.get("weekly_session_limit", 500)
print(f"Week started: {data['week_start']} | Limit: ~{limit} sessions/week | Alert: {data.get('alert_threshold_pct', 85)}%")
print()
total_sessions = 0
total_turns = 0
for acc, info in data["accounts"].items():
    s = info.get("weekly_sessions", len(info.get("sessions", [])))
    t = info.get("weekly_turns", 0)
    total_sessions += s
    total_turns += t
    pct = (s / limit) * 100 if limit > 0 else 0
    bar_len = min(int(pct / 5), 20)
    bar = "#" * bar_len + "-" * (20 - bar_len)
    status = "LIMIT!" if pct >= 85 else "OK"
    print(f"  {acc}")
    print(f"    [{bar}] {s} sessions, {t} turns ({pct:.0f}%) | {status}")
print()
print(f"  TOTAL: {total_sessions} sessions, {total_turns} turns (both accounts)")
PYEOF
}

# CLI
case "${1:-status}" in
    log)    init_usage_file; log_session "${2:-unknown}" "${3:-1}" ;;
    check)  init_usage_file; check_and_alert ;;
    status) show_status ;;
    init)   init_usage_file; echo "Initialized $USAGE_FILE" ;;
    *)      echo "Usage: $0 {status|log|check|init}" ;;
esac
