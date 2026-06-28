#!/bin/bash
# Stop hook: сохранить session state + auto-commit + push все 3 репо
# Заменяет sync-all-repos.sh — добавляет SESSION_STATE.json
set -euo pipefail

# --- mutual lock (macOS: нет flock; mkdir-atomic + PID-liveness reclaim) ---
# Замена mtime-эвристики (find -mmin +5): та могла украсть лок у ЛЕГИТ-прогона >5мин
# и допускала гонку двух забирающих (оба rmdir+mkdir). Теперь владелец пишет свой PID;
# занятый лок с ЖИВЫМ pid не трогаем; мёртвый/осиротевший pid забираем повторным
# атомарным mkdir (единственный арбитр гонки — кто первым mkdir, тот владелец).
# Stop-хук не критичен: не получили лок → тихо выходим 0 (синк сделает следующий цикл).
_GSLOCK=/tmp/artvision-git-sync.lock
_lock_acquire() {
  local tries=0 owner
  while ! mkdir "$_GSLOCK" 2>/dev/null; do
    owner="$(cat "$_GSLOCK/pid" 2>/dev/null || true)"
    if [ -n "$owner" ]; then
      if kill -0 "$owner" 2>/dev/null; then
        return 1                                 # владелец жив — не крадём
      fi
      rm -f "$_GSLOCK/pid" 2>/dev/null || true   # владелец мёртв → освободить;
      rmdir "$_GSLOCK" 2>/dev/null || true       # пере-захват атомарным mkdir на след. итерации
    else
      tries=$((tries + 1))                       # pid ещё не записан (чужой setup, ~мкс):
      if [ "$tries" -ge 10 ]; then               # после grace сочли осиротевшим — забрать
        rmdir "$_GSLOCK" 2>/dev/null || true
      else
        sleep 0.2
      fi
    fi
  done
  echo "$$" > "$_GSLOCK/pid"                      # заявить владение
  return 0
}
_lock_acquire || exit 0
trap 'rm -f "$_GSLOCK/pid" 2>/dev/null; rmdir "$_GSLOCK" 2>/dev/null' EXIT
# --- /lock ---

REPOS=(
    "$HOME/artvision-data"
    "$HOME/artvision-tg-bot"
    "$HOME/devops-agent"
)
STATE_FILE="$HOME/artvision-data/sync/SESSION_STATE.json"
DATE_COMMIT=$(date +%Y-%m-%d_%H:%M)
CURRENT_DIR="${PWD:-$(pwd)}"
SYNC_LOG_DIR="$HOME/artvision-data/logs/sync"
SYNC_FAIL_LOG="$SYNC_LOG_DIR/stop-sync-failures.log"
SYNC_FAILURES=()

mkdir -p "$SYNC_LOG_DIR"

record_sync_failure() {
    local repo="$1"
    local step="$2"
    local details="$3"
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    SYNC_FAILURES+=("$repo:$step")
    {
        printf '[%s] repo=%s step=%s\n' "$ts" "$repo" "$step"
        printf '%s\n\n' "$details"
    } >> "$SYNC_FAIL_LOG"
}

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

    repo_name="$(basename "$repo")"

    # GUARD против массовой потери данных (июнь 2026: 282 файла Грелки уехали в commit+push).
    # Проверяем ДО `git add -A`: >10 удалённых файлов → НЕ коммитим этот репо,
    # фиксируем как failure (данные целы), человек разрулит вручную.
    DELETED_CNT="$(git status --porcelain 2>/dev/null | grep -c '^ D\|^D ' || true)"
    if [ "${DELETED_CNT:-0}" -gt 10 ]; then
        record_sync_failure "$repo_name" "deletion-guard" "${DELETED_CNT} удалений (>10) — авто-commit отменён, вероятна потеря данных, разрулить вручную"
        continue
    fi

    # Добавить всё
    if ! ADD_ERR="$(git add -A 2>&1)"; then
        record_sync_failure "$repo_name" "git add" "$ADD_ERR"
        continue
    fi

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
    if ! COMMIT_ERR="$(git commit -m "sync: session state ${DATE_COMMIT}

Co-Authored-By: Claude <noreply@anthropic.com>" --quiet 2>&1)"; then
        record_sync_failure "$repo_name" "git commit" "$COMMIT_ERR"
        continue
    fi

    # Обновить локальную ветку перед push. Без этого non-fast-forward раньше
    # превращался в тихий рассинхрон из-за "|| true" на push.
    # ff-only: НЕ rebase. `pull --rebase --autostash` отвязывал локальные коммиты →
    # потеря данных (#9/#31; инцидент 28.06 stuck rebase + июнь — 282 файла Грелки).
    # Расхождение (non-ff) → фиксируем как failure, человек разрулит вручную (данные целы).
    if ! PULL_ERR="$(git pull --ff-only --quiet 2>&1)"; then
        record_sync_failure "$repo_name" "git pull --ff-only (non-ff → разрулить вручную)" "$PULL_ERR"
        continue
    fi

    # Push
    if ! PUSH_ERR="$(git push --quiet 2>&1)"; then
        record_sync_failure "$repo_name" "git push" "$PUSH_ERR"
        continue
    fi
done

# Вернуться в исходную директорию
cd "$CURRENT_DIR" 2>/dev/null || true

if [ "${#SYNC_FAILURES[@]}" -gt 0 ]; then
    {
        echo "⚠️  stop-sync-all: GitHub sync завершился с ошибками"
        echo "Репозитории/шаги: ${SYNC_FAILURES[*]}"
        echo "Лог: $SYNC_FAIL_LOG"
    } >&2
    exit 2
fi
