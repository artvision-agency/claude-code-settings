#!/bin/bash
# Stop hook: сохранить session state + auto-commit + push все 3 репо
# Заменяет sync-all-repos.sh — добавляет SESSION_STATE.json
set -euo pipefail

REPOS=(
    "$HOME/artvision-data"
    "$HOME/artvision-tg-bot"
    "$HOME/devops-agent"
)
STATE_FILE="$HOME/artvision-data/sync/SESSION_STATE.json"
DATE_COMMIT=$(date +%Y-%m-%d_%H:%M)
CURRENT_DIR="${PWD:-$(pwd)}"

# ═══════════════════════════════════════════════
# 1. Собрать session state через Python (безопасный JSON)
# ═══════════════════════════════════════════════

mkdir -p "$(dirname "$STATE_FILE")"

python3 << 'PYEOF'
import json, subprocess, os, re
from datetime import datetime
from pathlib import Path

HOME = os.path.expanduser("~")
STATE_FILE = os.path.join(HOME, "artvision-data/sync/SESSION_STATE.json")

repos_list = [
    os.path.join(HOME, "artvision-data"),
    os.path.join(HOME, "artvision-tg-bot"),
    os.path.join(HOME, "devops-agent"),
]

todo_files = [
    os.path.join(HOME, "artvision-data/TODO.md"),
    os.path.join(HOME, "artvision-tg-bot/TODO.md"),
    os.path.join(HOME, "devops-agent/TODO.md"),
    os.path.join(HOME, "artvision-data/presale/TODO.md"),
    os.path.join(HOME, "artvision-data/products/TODO.md"),
]

# --- Repos: branch + dirty ---
repos = {}
for repo in repos_list:
    if os.path.isdir(os.path.join(repo, ".git")):
        name = os.path.basename(repo)
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=repo, stderr=subprocess.DEVNULL
            ).decode().strip() or "detached"
        except Exception:
            branch = "unknown"
        try:
            porcelain = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=repo, stderr=subprocess.DEVNULL
            ).decode().strip()
            dirty = bool(porcelain)
        except Exception:
            dirty = False
        repos[name] = {"branch": branch, "dirty": dirty}

# --- Last task context from SYNC_STATUS.md ---
last_task_context = ""
sync_status = os.path.join(HOME, "artvision-data/sync/SYNC_STATUS.md")
if os.path.isfile(sync_status):
    try:
        with open(sync_status, "r") as f:
            lines = f.readlines()
        found = False
        for line in lines:
            if found and line.strip().startswith("- "):
                last_task_context = line.strip().lstrip("- ").strip()
                break
            if "Значимые коммиты" in line:
                found = True
    except Exception:
        pass

# --- Pending tasks from TODO.md files ---
pending = []
pattern = re.compile(r'^\s*- \[ \] (.+)')
for todo_file in todo_files:
    if not os.path.isfile(todo_file):
        continue
    try:
        with open(todo_file, "r") as f:
            for line in f:
                m = pattern.match(line)
                if m:
                    task = m.group(1).strip()[:200]
                    if task:
                        pending.append(task)
                if len(pending) >= 80:
                    break
    except Exception:
        continue

# --- Session duration (from env) ---
duration = 0
start = os.environ.get("CLAUDE_SESSION_START", "")
if start:
    try:
        import time
        duration = int((time.time() - int(start)) / 60)
    except Exception:
        pass

# --- Account ---
account = os.environ.get("CLAUDE_ACCOUNT", "unknown")
if account == "unknown":
    try:
        out = subprocess.check_output(
            ["claude", "auth", "status", "--json"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode()
        data = json.loads(out)
        account = data.get("email", "unknown")
    except Exception:
        pass

# --- Write JSON ---
state = {
    "timestamp": datetime.now().strftime("%Y-%m-%d_%H:%M"),
    "current_dir": os.environ.get("PWD", os.getcwd()),
    "repos": repos,
    "last_task_context": last_task_context,
    "pending_tasks": pending,
    "session_duration_min": duration,
    "account": account,
}

with open(STATE_FILE, "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
PYEOF

# ═══════════════════════════════════════════════
# 2. Log session stats (из оригинального sync-all-repos.sh)
# ═══════════════════════════════════════════════

python3 "$HOME/artvision-data/scripts/session_logger.py" 2>/dev/null || true
python3 "$HOME/artvision-data/scripts/session_to_asana.py" 2>/dev/null || true

# ═══════════════════════════════════════════════
# 2.5. Context Bridge: синхронизация контекста TG-бот <-> Claude Code
# ═══════════════════════════════════════════════

"$HOME/.claude/scripts/context-bridge.sh" 2>/dev/null || true

# ═══════════════════════════════════════════════
# 3. Auto-commit + push каждый репо
# ═══════════════════════════════════════════════

for repo in "${REPOS[@]}"; do
    if [ ! -d "$repo/.git" ]; then
        continue
    fi

    cd "$repo"

    # Проверить есть ли изменения
    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
        continue
    fi

    # Добавить всё
    git add -A 2>/dev/null || true

    # Удалить из staging опасные файлы (credentials, env, keys, node_modules)
    # tokens.json* и *.bak добавлены 2026-05-29: хук пушил token-бэкапы с API-ключами
    # на remote (корень self-corrections #20). Defense-in-depth поверх .gitignore.
    git reset HEAD -- \
        '*.env' '*.env.*' '*.env.local' '*.env.production' \
        '.env' '.env.*' \
        'credentials*' 'secrets.json' \
        '*.pem' '*.key' '*_secret*' \
        'tokens.json' 'tokens.json.bak*' 'tokens_backup_*.json' \
        '*.bak' '*.bak.*' '*.bak-*' '*.bak_*' \
        2>/dev/null || true
    git rm --cached -r node_modules/ 2>/dev/null || true

    # Проверить что есть что коммитить после очистки
    if [ -z "$(git diff --cached --name-only 2>/dev/null)" ]; then
        continue
    fi

    # Коммит
    git commit -m "sync: session state ${DATE_COMMIT}

Co-Authored-By: Claude <noreply@anthropic.com>" --quiet 2>/dev/null || true

    # Push
    git push --quiet 2>/dev/null || true
done

# Вернуться в исходную директорию
cd "$CURRENT_DIR" 2>/dev/null || true
