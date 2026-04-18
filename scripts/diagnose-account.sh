#!/bin/bash
# diagnose-account.sh — Диагностика аккаунта Claude Max
# Показывает текущий аккаунт, расход, модели, проблемы
set -euo pipefail

OUTPUT="/tmp/account-diagnosis-$(date +%Y-%m-%d).md"
PROJECTS_DIR="$HOME/.claude/projects"
TELEMETRY_DIR="$HOME/.claude/telemetry"

echo "# Диагностика Claude Max Account — $(date '+%Y-%m-%d %H:%M')" > "$OUTPUT"
echo "" >> "$OUTPUT"

# 1. Текущий аккаунт (из usage tracker)
echo "## 1. Расход по аккаунтам" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
"$HOME/.claude/scripts/account-usage-tracker.sh" status 2>/dev/null >> "$OUTPUT" || echo "Трекер недоступен" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
echo "" >> "$OUTPUT"

# 2. Модели в последних N сессиях
echo "## 2. Модели в последних 20 сессиях" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "| Дата | Session ID | Модель | Prompt |" >> "$OUTPUT"
echo "|------|-----------|--------|--------|" >> "$OUTPUT"

python3 << 'PYEOF' >> "$OUTPUT"
import json, os, glob
from datetime import datetime

sessions = []
for pattern in [os.path.expanduser("~/.claude/projects/-Users-antonk/*.jsonl"),
                os.path.expanduser("~/.claude/projects/-Users-antonk-artvision-data/*.jsonl")]:
    for f in glob.glob(pattern):
        if '/subagents/' in f:
            continue
        mtime = os.path.getmtime(f)
        sessions.append((f, mtime))

sessions.sort(key=lambda x: x[1], reverse=True)

for f, mtime in sessions[:20]:
    mod = datetime.fromtimestamp(mtime).strftime("%d.%m %H:%M")
    basename = os.path.basename(f)[:12]
    models = set()
    prompt = ""
    with open(f) as fh:
        for line in fh:
            try:
                d = json.loads(line.strip())
                msg = d.get('message', {})
                if isinstance(msg, dict):
                    model = msg.get('model', '')
                    if model and model != '<synthetic>' and model != 'N/A':
                        models.add(model)
                    if d.get('type') == 'user' and not prompt:
                        content = msg.get('content', '')
                        if isinstance(content, str):
                            prompt = content[:60].replace('|', '/').replace('\n', ' ')
            except:
                pass
    models_str = ', '.join(models) if models else 'N/A'
    flag = ''
    for m in models:
        if 'haiku' in m: flag = ' **HAIKU!**'
        elif 'sonnet' in m: flag = ' **SONNET!**'
    print(f"| {mod} | {basename} | {models_str}{flag} | {prompt} |")
PYEOF

echo "" >> "$OUTPUT"

# 3. Rate limit / downgrade в телеметрии
echo "## 3. Rate Limit / Downgrade (последние 7 дней)" >> "$OUTPUT"
echo "" >> "$OUTPUT"

python3 << 'PYEOF' >> "$OUTPUT"
import json, os, glob, re
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=7)
files = glob.glob(os.path.expanduser("~/.claude/telemetry/1p_failed_events.*.json"))
downgrades = []
for f in sorted(files, key=os.path.getmtime):
    mtime = os.path.getmtime(f)
    mod = datetime.fromtimestamp(mtime)
    if mod < cutoff: continue
    try:
        haiku_count = sonnet_count = opus_count = 0
        emails = set()
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line: continue
                try:
                    evt = json.loads(line)
                    ed = evt.get('event_data', evt)
                    model = ed.get('model', '')
                    email = ed.get('email', '')
                    if email: emails.add(email)
                    if 'haiku' in model: haiku_count += 1
                    elif 'sonnet' in model: sonnet_count += 1
                    elif 'opus' in model: opus_count += 1
                except: pass
        if haiku_count > 0 or sonnet_count > 0:
            email_str = ', '.join(emails) if emails else 'unknown'
            downgrades.append(f"- **{mod.strftime('%d.%m %H:%M')}** | {email_str} | opus:{opus_count} sonnet:{sonnet_count} haiku:{haiku_count}")
    except: pass

if downgrades:
    print("**DOWNGRADES DETECTED:**\n")
    for d in downgrades: print(d)
else:
    print("No downgrades in last 7 days.")
PYEOF

echo "" >> "$OUTPUT"

# 4. Settings
echo "## 4. Settings (model overrides)" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
python3 -c "
import json, os
s = os.path.expanduser('~/.claude/settings.json')
if os.path.exists(s):
    d = json.load(open(s))
    env = d.get('env', {})
    print(f'AGENT_TEAMS: {env.get(\"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS\", \"not set\")}')
    for k,v in env.items():
        if 'model' in k.lower(): print(f'env.{k}: {v}')
" >> "$OUTPUT" 2>/dev/null
echo '```' >> "$OUTPUT"

echo ""
echo "=== Diagnosis complete ==="
echo "Report: $OUTPUT"
cat "$OUTPUT"
