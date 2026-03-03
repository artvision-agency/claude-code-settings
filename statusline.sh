#!/bin/bash
# Claude Code Statusline — Artvision
# Показывает: пользователь | модель | папка | git ветка* | контекст% | стоимость

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

parts = [user, model, dir_short]
if git_info:
    parts.append(git_info)
parts.append(f'{ctx}:{pct}%')
parts.append(f'\${cost:.2f}')

print(' | '.join(parts))
"
