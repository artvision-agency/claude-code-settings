#!/usr/bin/env bash
# post-compact-tasks.sh — после compaction извлекает Pending Tasks из summary
# Подключается к SessionStart:compact hook
set -euo pipefail

# Найти последний summary в session jsonl
SESSION_DIR="$HOME/.claude/projects/-Users-antonk"
LATEST=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1)
[ -z "$LATEST" ] && exit 0

# Извлечь последний summary блок и найти Pending Tasks секцию
python3 << PYEOF
import json, re, sys
from pathlib import Path

f = Path("$LATEST")
summary = None
try:
    for line in f.read_text(errors='ignore').splitlines():
        try:
            j = json.loads(line)
            if isinstance(j, dict) and j.get('type') == 'summary':
                summary = j.get('summary') or j.get('content', '')
        except: pass
except: sys.exit(0)

if not summary:
    sys.exit(0)

# Найти Pending Tasks секцию
m = re.search(r'(?:Pending Tasks|7\.\s*Pending)[\s\S]{0,3000}?(?=\n\d+\.|\n##|\Z)', summary, re.I)
if not m:
    sys.exit(0)

# Извлечь bullet items
items = re.findall(r'(?:^|\n)\s*[-\*]\s*(.+)', m.group(0))
items = [i.strip() for i in items if i.strip() and len(i) > 5][:15]

if items:
    print("═══ POST-COMPACT: PENDING из summary ═══")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item[:120]}")
    print("═══ → создай TaskCreate для каждого ═══")
PYEOF
