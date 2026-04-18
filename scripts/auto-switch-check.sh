#!/bin/bash
# Auto Switch Check — проверка usage обоих аккаунтов + рекомендация
# Использование: auto-switch-check.sh [--for-combine]
set -euo pipefail

USAGE_FILE="$HOME/.claude/account-usage.json"
WARNING_FLAG="/tmp/claude-account-warning.flag"
NOTIFY="$HOME/.claude/scripts/notify-telegram.sh"

ACC1="justtrance@gmail.com"
ACC2="adw.artvision.pro@gmail.com"

# Получить текущий аккаунт
get_current() {
    claude auth status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('email','unknown'))" 2>/dev/null || echo "unknown"
}

# Рассчитать usage и время до сброса
check_accounts() {
    python3 << 'PYEOF'
import json, os, sys
from datetime import datetime, timedelta

fpath = os.path.expanduser("~/.claude/account-usage.json")
if not os.path.exists(fpath):
    print("NO_DATA")
    sys.exit(0)

with open(fpath) as f:
    data = json.load(f)

limit = data.get("weekly_session_limit", 500)
week_start = datetime.strptime(data.get("week_start", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")

# Время до сброса (понедельник 03:00 MSK)
now = datetime.now()
days_until_monday = (7 - now.weekday()) % 7
if days_until_monday == 0 and now.hour >= 3:
    days_until_monday = 7
reset_date = now.replace(hour=3, minute=0, second=0) + timedelta(days=days_until_monday)
hours_until_reset = max(0, int((reset_date - now).total_seconds() / 3600))

results = []
for email, info in data.get("accounts", {}).items():
    sessions = info.get("weekly_sessions", 0)
    turns = info.get("weekly_turns", 0)
    pct = min(100, int(sessions / limit * 100)) if limit > 0 else 0
    short = email.split("@")[0][:12]
    results.append({
        "email": email,
        "short": short,
        "sessions": sessions,
        "turns": turns,
        "pct": pct,
        "hours_reset": hours_until_reset
    })

# Вывод таблицы
print(f"{'Аккаунт':<20} {'Sessions':>8} {'Usage':>6} {'До сброса':>12}")
print("-" * 50)
for r in results:
    bar = "█" * (r["pct"] // 10) + "░" * (10 - r["pct"] // 10)
    reset_str = f"{r['hours_reset']}ч ({r['hours_reset']//24}д)"
    print(f"{r['short']:<20} {r['sessions']:>8} {r['pct']:>5}% {reset_str:>12}")

# Рекомендация
sorted_r = sorted(results, key=lambda x: x["pct"])
best = sorted_r[0]

print()
if all(r["pct"] >= 90 for r in results):
    print("🔴 ОБА аккаунта >90%! Ждать сброса или купить доп. лимит.")
elif best["pct"] < 50:
    print(f"✅ Рекомендация: {best['short']} ({best['pct']}%)")
elif best["pct"] < 80:
    print(f"🟡 Рекомендация: {best['short']} ({best['pct']}%), расходуй экономно")
else:
    print(f"🟠 Оба аккаунта загружены. Лучший: {best['short']} ({best['pct']}%)")

# Для combine: вывести email лучшего
if "--for-combine" in sys.argv:
    if all(r["pct"] >= 90 for r in results):
        print(f"\nCOMBINE_BLOCKED=true")
    else:
        print(f"\nCOMBINE_ACCOUNT={best['email']}")
        print(f"COMBINE_BLOCKED=false")

# Алерты
for r in results:
    if r["pct"] >= 97:
        print(f"\nALERT_URGENT={r['email']}")
    elif r["pct"] >= 95:
        print(f"\nALERT_HIGH={r['email']}")
    elif r["pct"] >= 90:
        print(f"\nALERT_WARNING={r['email']}")
PYEOF
}

# Основной запуск
OUTPUT=$(check_accounts)
echo "$OUTPUT"

# Проверить алерты и отправить в TG
if echo "$OUTPUT" | grep -q "ALERT_URGENT"; then
    ALERT_ACC=$(echo "$OUTPUT" | grep "ALERT_URGENT" | cut -d= -f2)
    if [ -x "$NOTIFY" ]; then
        $NOTIFY "🔴 URGENT: $ALERT_ACC на 97%+ лимита! Переключись: ~/.claude/scripts/switch-account.sh"
    fi
    touch "$WARNING_FLAG"
fi

if echo "$OUTPUT" | grep -q "ALERT_HIGH"; then
    ALERT_ACC=$(echo "$OUTPUT" | grep "ALERT_HIGH" | cut -d= -f2)
    if [ -x "$NOTIFY" ]; then
        $NOTIFY "🟠 WARNING: $ALERT_ACC на 95%+ лимита. Рекомендуем переключиться."
    fi
fi

# Для combine: проверить блокировку
if [ "${1:-}" = "--for-combine" ]; then
    if echo "$OUTPUT" | grep -q "COMBINE_BLOCKED=true"; then
        echo "BLOCKED" >&2
        exit 1
    fi
fi
