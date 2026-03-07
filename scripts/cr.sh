#!/bin/zsh
source ~/.zshrc 2>/dev/null
# Получить session ID по номеру
SESSION_ID=$(python3 -c "
import json, sys
from pathlib import Path
from datetime import datetime

sessions = []
for pd in (Path.home()/'.claude'/'projects').iterdir():
    if not pd.is_dir(): continue
    for f in pd.glob('*.jsonl'):
        sessions.append((f.stem, f.stat().st_mtime))
sessions.sort(key=lambda x: x[1], reverse=True)
idx = int(sys.argv[1]) - 1
print(sessions[idx][0])
" "$1" 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
    echo "Session $1 not found"
    read -k1
    exit 1
fi

exec command claude --dangerously-skip-permissions --resume "$SESSION_ID"
