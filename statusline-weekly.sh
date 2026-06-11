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
sessions = usage.setdefault('sessions', {})
now = time.time()
if sid:
    sessions[sid] = {'cost': cost, 'ts': now}
cutoff = now - 7 * 86400
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

limit = usage.get('weekly_limit_usd') or 0
week_info = ''
if limit:
    wpct = int(weekly / limit * 100)
    mark = 'W!' if wpct >= 97 else ('w!' if wpct >= 80 else ('w*' if wpct >= 50 else 'w'))
    week_info = f'{mark}:${weekly:.0f}/{limit:.0f} ({wpct}%)'

parts = [user, model, dir_short]
if git_info:
    parts.append(git_info)
parts.append(f'{ctx}:{pct}%')
parts.append(f'${cost:.2f}')
if week_info:
    parts.append(week_info)

print(' | '.join(parts))
PY
