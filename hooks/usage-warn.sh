#!/bin/bash
# UserPromptSubmit hook: предупреждение о недельном расходе из ~/.claude/account-usage.json.
# Срабатывает при входе в новую полосу (50/60/70/80/90/97%) либо раз в 6 часов внутри полосы.
# systemMessage — видит пользователь; additionalContext — видит модель.
python3 - <<'PY'
import json, os, time

home = os.path.expanduser('~')
usage_path = os.path.join(home, '.claude', 'account-usage.json')
state_path = os.path.join(home, '.claude', '.usage-warn-state.json')

try:
    u = json.load(open(usage_path))
except Exception:
    raise SystemExit(0)

limit = u.get('weekly_limit_usd') or 0
cost = u.get('weekly_cost') or 0
if not limit:
    raise SystemExit(0)

pct = cost / limit * 100
band = max((b for b in (50, 60, 70, 80, 90, 97) if pct >= b), default=0)
if band == 0:
    raise SystemExit(0)

st = {}
try:
    st = json.load(open(state_path))
except Exception:
    pass
now = time.time()
if st.get('band') == band and now - st.get('ts', 0) < 6 * 3600:
    raise SystemExit(0)
try:
    json.dump({'band': band, 'ts': now}, open(state_path, 'w'))
except Exception:
    pass

msg = f"Недельный расход Claude: ${cost:.0f} из ${limit:.0f} ({pct:.0f}%)."
print(json.dumps({
    'systemMessage': msg,
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': f"[usage-warn] {msg} Сообщи пользователю и учитывай при планировании тяжёлых операций (волны субагентов и т.п.).",
    },
}, ensure_ascii=False))
PY
exit 0
