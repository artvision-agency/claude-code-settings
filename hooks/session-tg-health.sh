#!/bin/bash
# SessionStart: показать РЕАЛЬНЫЙ статус Telethon-сессии (@username) во всех сессиях.
# Источник: кэш ~/.claude/state/tg-session-status.json (пишет tg-session-health.py).
# Кэш старше 6ч → обновление в ФОНЕ (не тормозит старт), показываем прошлое значение с пометкой.
# Запрос Антона 2026-06-10: «Telethon жив — надо чтобы во ВСЕХ сессиях это было видно».
# Bypass: TG_HEALTH_OFF=1
set -u
[ "${TG_HEALTH_OFF:-0}" = "1" ] && exit 0

CACHE="$HOME/.claude/state/tg-session-status.json"
CHECKER="$HOME/.claude/scripts/tg-session-health.py"
MAX_AGE=$((6*3600))

refresh_bg() {
  ( nohup python3 "$CHECKER" >/dev/null 2>&1 & ) >/dev/null 2>&1
}

if [ ! -f "$CACHE" ]; then
  refresh_bg
  echo "📡 TG (Telethon): статус ещё не снят — проверка запущена в фоне (увидишь в следующей сессии)"
  exit 0
fi

NOW=$(date +%s)
python3 - "$CACHE" "$NOW" "$MAX_AGE" << 'PYEOF'
import json, sys, time
cache, now, max_age = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
try:
    d = json.load(open(cache))
except Exception:
    print("📡 TG (Telethon): кэш повреждён — обновляю в фоне"); sys.exit(3)
age = now - d.get("checked_at", 0)
stale = age > max_age
ts = d.get("checked_at_human", "?")
st = d.get("status")
if st == "alive":
    p = d.get("primary") or {}
    u = p.get("username") or "?"
    sess = (p.get("session") or "").split("/")[-1]
    mark = " ⏳(кэш устарел, обновляю в фоне)" if stale else ""
    print(f"📡 TG (Telethon): ✅ ЖИВ — @{u} ({sess}, проверено {ts}){mark}")
elif st == "no-creds":
    print(f"📡 TG (Telethon): 🔴 api_id/api_hash отсутствуют в tokens.json (проверено {ts})")
elif st == "dead":
    print(f"📡 TG (Telethon): 🔴 сессии НЕ авторизованы (проверено {ts}) → re-auth: scripts/tg-signin-relay.py")
else:
    print(f"📡 TG (Telethon): ⚠️ {d.get('detail','ошибка проверки')} (проверено {ts})")
sys.exit(3 if stale else 0)
PYEOF
RC=$?
[ "$RC" = "3" ] && refresh_bg
exit 0
