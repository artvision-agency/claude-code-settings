#!/bin/bash
# Claude Code Statusline — Artvision
# Показывает: пользователь | модель | папка | git ветка* | контекст% | стоимость | week$

python3 -c "
import sys, json, subprocess, os

data = json.load(sys.stdin)

model = data.get('model', {}).get('display_name', '?')
pct = int(float(data.get('context_window', {}).get('used_percentage', 0)))
cost = float(data.get('cost', {}).get('total_cost_usd', 0))
cwd = data.get('cwd', os.getcwd())

user = os.environ.get('USER', 'user')
dir_short = os.path.basename(cwd)

# Git branch + dirty
git_info = ''
try:
    branch = subprocess.check_output(['git', '-C', cwd, 'branch', '--show-current'], stderr=subprocess.DEVNULL, timeout=2).decode().strip()
    if branch:
        dirty = ''
        try:
            subprocess.check_call(['git', '-C', cwd, 'diff', '--quiet'], stderr=subprocess.DEVNULL, timeout=2)
        except:
            dirty = '*'
        if not dirty:
            try:
                subprocess.check_call(['git', '-C', cwd, 'diff', '--cached', '--quiet'], stderr=subprocess.DEVNULL, timeout=2)
            except:
                dirty = '*'
        git_info = f'{branch}{dirty}'
except:
    pass

# Context indicator
ctx = 'CTX!' if pct >= 80 else ('ctx!' if pct >= 60 else 'ctx')

# Weekly account usage from tracker
week_info = ''
try:
    usage_file = os.path.expanduser('~/.claude/account-usage.json')
    if os.path.exists(usage_file):
        with open(usage_file) as f:
            usage = json.load(f)
        # Detect current account from env or auth
        email = os.environ.get('CLAUDE_EMAIL', '')
        if not email:
            try:
                r = subprocess.check_output(['claude', 'auth', 'status', '--json'], stderr=subprocess.DEVNULL, timeout=3).decode()
                email = json.loads(r).get('email', '')
            except:
                pass
        if email and email in usage.get('accounts', {}):
            weekly_cost = usage['accounts'][email].get('weekly_cost', 0)
            limit = usage.get('weekly_limit_usd', 150)
            wpct = int((weekly_cost / limit) * 100) if limit > 0 else 0
            if wpct >= 97:
                week_info = f'W!\${weekly_cost:.0f}'
            elif wpct >= 80:
                week_info = f'w!\${weekly_cost:.0f}'
            else:
                week_info = f'w:\${weekly_cost:.0f}'
except:
    pass

parts = [user, model, dir_short]
if git_info:
    parts.append(git_info)
parts.append(f'{ctx}:{pct}%')
parts.append(f'\${cost:.2f}')
if week_info:
    parts.append(week_info)

print(' | '.join(parts))
"
