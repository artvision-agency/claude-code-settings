#!/bin/bash
# Установка: реальные лимиты плана (/api/oauth/usage, тот же источник, что /usage)
# в статуслайне + активные предупреждения. Идемпотентно.
#
# Что делает:
#   1. кладёт statusline.sh, usage-refresh.sh, hooks/usage-warn.sh в ~/.claude
#   2. прописывает в ~/.claude/settings.json statusLine и UserPromptSubmit-хук
#      (существующие ключи/секреты сохраняются)
#
# Запуск:  bash install.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.claude"
mkdir -p "$DST/hooks"

cp "$SRC/statusline.sh"        "$DST/statusline.sh"
cp "$SRC/usage-refresh.sh"     "$DST/usage-refresh.sh"
cp "$SRC/hooks/usage-warn.sh"  "$DST/hooks/usage-warn.sh"
chmod +x "$DST/statusline.sh" "$DST/usage-refresh.sh" "$DST/hooks/usage-warn.sh"
echo "✅ Скрипты скопированы в $DST"

# бэкап settings.json
[ -f "$DST/settings.json" ] && cp "$DST/settings.json" "$DST/settings.json.bak.usage-statusline"

python3 - "$DST/settings.json" <<'PY'
import json, os, sys
p = sys.argv[1]
home = os.path.expanduser('~')
try:
    s = json.load(open(p))
except Exception:
    s = {}

# statusLine -> наш скрипт
s['statusLine'] = {'type': 'command', 'command': f'{home}/.claude/statusline.sh'}

# UserPromptSubmit -> usage-warn.sh (без дублей)
cmd = f'{home}/.claude/hooks/usage-warn.sh'
ups = s.setdefault('hooks', {}).setdefault('UserPromptSubmit', [])
exists = any(h.get('command') == cmd for grp in ups for h in grp.get('hooks', []))
if not exists:
    ups.append({'hooks': [{'type': 'command', 'command': cmd, 'timeout': 10}]})

json.dump(s, open(p, 'w'), ensure_ascii=False, indent=2)
print('✅ settings.json обновлён (statusLine + usage-warn хук); бэкап рядом .bak.usage-statusline')
PY

echo
echo "Готово. Перезапусти сессию Claude Code — в статуслайне появятся 5h:N% wk:N%."
echo "Проверка вручную:  bash $DST/usage-refresh.sh && cat $DST/.usage-cache.json"
