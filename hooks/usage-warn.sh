#!/bin/bash
# UserPromptSubmit hook: предупреждение о реальных лимитах плана из /api/oauth/usage
# (тот же источник, что /usage). Читает кэш ~/.claude/.usage-cache.json, который держит
# свежим статуслайн; если кэш устарел — пинает фоновый usage-refresh.sh (prompt не блокируем),
# а кэш старше 10 мин не используется вовсе (иначе после простоя сессии врут проценты окна).
# Срабатывает при входе в новую полосу либо раз в 6 ч внутри полосы — отдельно по неделе и 5ч-окну.
# systemMessage — видит пользователь; additionalContext — видит модель.
python3 - <<'PY'
import json, os, time, subprocess

home = os.path.expanduser('~')
cache_path = os.path.join(home, '.claude', '.usage-cache.json')
state_path = os.path.join(home, '.claude', '.usage-warn-state.json')
refresh = os.path.join(home, '.claude', 'usage-refresh.sh')
now = time.time()

# держим кэш свежим без блокировки prompt
try:
    cache_age = now - os.path.getmtime(cache_path)
except OSError:
    cache_age = 1e9
if cache_age > 120 and os.path.exists(refresh):
    try:
        subprocess.Popen(['bash', refresh], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception:
        pass

# кэш старше 10 минут (сессия простояла) — цифры окна могли давно сброситься;
# молчим, refresh выше уже запущен, следующий prompt получит свежие данные
if cache_age > 600:
    raise SystemExit(0)

try:
    api = json.load(open(cache_path))
except Exception:
    raise SystemExit(0)

# (ключ_состояния, ярлык, объект окна, полосы%)
windows = [
    ('wk', 'недельный лимит (все модели)', api.get('seven_day'),  (85, 90, 95, 97)),
    ('5h', '5-часовое окно сессии (общее по аккаунту)', api.get('five_hour'), (50, 80, 95)),
]

try:
    st = json.load(open(state_path))
except Exception:
    st = {}

msgs = []
changed = False
for key, label, win, bands in windows:
    util = (win or {}).get('utilization')
    if util is None:
        continue
    pct = int(round(util))
    band = max((b for b in bands if pct >= b), default=0)
    prev = st.get(key, {})
    if band == 0:
        if prev:              # упало ниже порога (напр. сброс окна) — забываем
            st[key] = {}
            changed = True
        continue
    if prev.get('band') != band or now - prev.get('ts', 0) >= 6 * 3600:
        st[key] = {'band': band, 'ts': now}
        changed = True
        msgs.append(f'{label} — {pct}%')

if changed:
    try:
        json.dump(st, open(state_path, 'w'))
    except Exception:
        pass

if not msgs:
    raise SystemExit(0)

msg = 'Лимиты Claude: ' + '; '.join(msgs) + '.'
print(json.dumps({
    'systemMessage': '⚠️ ' + msg,
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': f"[usage-warn] {msg} Сообщи пользователю и учитывай при планировании тяжёлых операций (волны субагентов и т.п.).",
    },
}, ensure_ascii=False))
PY
exit 0
