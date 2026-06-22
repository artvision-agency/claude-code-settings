#!/bin/bash
# Claude Code statusline + недельный учёт расхода (адаптация artvision statusline.sh).
# stdin: JSON от Claude Code (model, context_window, cost, session_id, cwd).
# Side effect: обновляет ~/.claude/account-usage.json — rolling 7-дневная сумма
# total_cost_usd по сессиям. Файл читают: эта статус-строка и hook usage-warn.sh.
# stdin читаем в переменную ДО python: heredoc-программа сама занимает stdin.
CC_STATUS_JSON=$(cat 2>/dev/null || true)
export CC_STATUS_JSON
python3 - <<'PY'
import sys, json, os, time, subprocess, tempfile

try:
    data = json.loads(os.environ.get('CC_STATUS_JSON') or '{}')
except Exception:
    data = {}

home = os.path.expanduser('~')
usage_path = os.path.join(home, '.claude', 'account-usage.json')

model = data.get('model', {}).get('display_name', '?')
pct = int(float(data.get('context_window', {}).get('used_percentage', 0) or 0))
cost = float(data.get('cost', {}).get('total_cost_usd', 0) or 0)
cwd = data.get('cwd') or os.getcwd()
sid = data.get('session_id', '')

# --- недельный трекер: upsert текущей сессии (cost кумулятивный), чистка >7 дней ---
usage = {}
try:
    with open(usage_path) as f:
        usage = json.load(f)
except Exception:
    usage = {}
usage.setdefault('weekly_limit_usd', 150)
# Якорь недельного сброса плана Anthropic (как в /usage: «Resets …, 21:00 Europe/Moscow»).
# Дефолт — 2026-06-19 18:00 UTC = 21:00 MSK; сброс раз в 7 суток. Меняется в
# account-usage.json -> week_reset_anchor (epoch UTC), если в /usage другой день/время.
anchor = usage.setdefault('week_reset_anchor', 1781892000)
sessions = usage.setdefault('sessions', {})
now = time.time()
if sid:
    sessions[sid] = {'cost': cost, 'ts': now}
# Окно НЕ скользящее: начало = последний плановый сброс ≤ now. Так недельная сумма
# обнуляется в момент ресета плана, а не «висит» как при rolling-7d.
week = 7 * 86400
cutoff = anchor + ((now - anchor) // week) * week
for k in [k for k, v in sessions.items() if v.get('ts', 0) < cutoff]:
    del sessions[k]
weekly = round(sum(v.get('cost', 0) for v in sessions.values()), 2)
usage['weekly_cost'] = weekly
usage['updated_at'] = int(now)
try:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(usage_path))
    with os.fdopen(fd, 'w') as f:
        json.dump(usage, f, ensure_ascii=False, indent=1)
    os.replace(tmp, usage_path)
except Exception:
    pass

user = os.environ.get('USER', 'user')
try:
    hostname = subprocess.check_output(['hostname', '-s'], timeout=2).decode().strip()
except Exception:
    hostname = ''
dir_short = os.path.basename(cwd)

git_info = ''
try:
    branch = subprocess.check_output(
        ['git', '-C', cwd, 'branch', '--show-current'],
        stderr=subprocess.DEVNULL, timeout=2).decode().strip()
    if branch:
        dirty = ''
        for args in (['diff', '--quiet'], ['diff', '--cached', '--quiet']):
            try:
                subprocess.check_call(['git', '-C', cwd] + args,
                                      stderr=subprocess.DEVNULL, timeout=2)
            except Exception:
                dirty = '*'
                break
        git_info = f'{branch}{dirty}'
except Exception:
    pass

ctx = 'CTX!' if pct >= 80 else ('ctx!' if pct >= 60 else 'ctx')

# --- реальные лимиты плана из /api/oauth/usage (тот же источник, что /usage) ---
# Кэш обновляет фоновый usage-refresh.sh не чаще раза в TTL, чтобы не дёргать API на каждый рендер.
USAGE_TTL = 60
cache_path = os.path.join(home, '.claude', '.usage-cache.json')
attempt_path = os.path.join(home, '.claude', '.usage-refresh.attempt')
try:
    cache_age = now - os.path.getmtime(cache_path)
except OSError:
    cache_age = 1e9
if cache_age > USAGE_TTL:
    try:
        last_try = now - os.path.getmtime(attempt_path)
    except OSError:
        last_try = 1e9
    if last_try > 10:  # не плодить фоновые curl чаще раза в 10с
        try:
            open(attempt_path, 'w').close()
            subprocess.Popen(
                ['bash', os.path.join(home, '.claude', 'usage-refresh.sh')],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception:
            pass

def _fmt_reset(resets_at):
    # resets_at — ISO8601 с tz (UTC). Возвращаем точное время сброса в локальном tz:
    # сегодня -> "12:49", иначе -> "Jun19 20:59".
    if not resets_at:
        return ''
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(resets_at).astimezone()   # -> локальная зона
        loc_now = datetime.fromtimestamp(now).astimezone()
    except Exception:
        return ''
    if dt.date() == loc_now.date():
        return dt.strftime('%H:%M')
    return dt.strftime('%b%d %H:%M')

def _fmt_window(label, util, resets_at=None):
    p = int(round(util))
    if p >= 80:
        c = '\033[31m'   # красный — лимит на исходе
    elif p >= 50:
        c = '\033[33m'   # жёлтый — перевалило за половину
    else:
        c = '\033[32m'   # зелёный
    r = _fmt_reset(resets_at)
    tail = f' \033[90m({r})\033[0m' if r else ''   # серый — время до сброса окна
    return f'{c}{label}:{p}%\033[0m{tail}'

week_info = ''
try:
    with open(cache_path) as f:
        api = json.load(f)
    segs = []
    five = api.get('five_hour') or {}
    seven = api.get('seven_day') or {}
    fh = five.get('utilization')        # 5-часовое окно (общее по аккаунту)
    sd = seven.get('utilization')       # недельный лимит (все модели)
    if fh is not None:
        segs.append(_fmt_window('5h', fh, five.get('resets_at')))
    if sd is not None:
        segs.append(_fmt_window('wk', sd, seven.get('resets_at')))
    if segs:
        stale = ' ~' if cache_age > 300 else ''  # данные старше 5 мин (нет сети / токен протух)
        week_info = '   '.join(segs) + stale
except Exception:
    week_info = ''

user_host = f'{user}@{hostname}' if hostname else user
parts = [user_host, model, dir_short]
if git_info:
    parts.append(git_info)
# ~/.claude/statusline.hide скрывает блок метрик (toggle: statusline-toggle); учёт расходов выше работает всегда
if not os.path.exists(os.path.join(home, '.claude', 'statusline.hide')):
    parts.append(f'{ctx}:{pct}%')
    parts.append(f'${cost:.2f}')
    # me: мой $-расход ЭТОЙ машины за неделю как % от своего $-лимита (weekly_limit_usd).
    # Окно совпадает с wk (тот же anchor). Цвета — как у лимитов (_fmt_window).
    wl = usage.get('weekly_limit_usd') or 0
    if wl > 0:
        parts.append(_fmt_window('me', weekly / wl * 100))
    if week_info:
        parts.append(week_info)

print(' | '.join(parts))
PY
