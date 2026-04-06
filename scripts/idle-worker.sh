#!/bin/bash
set -euo pipefail

# Idle Worker — автономный комбайн
# Если Claude не используется 30 мин → берёт задачу из Asana и выполняет
# LaunchAgent: pro.artvision.idle-worker (каждые 5 мин)

LOG="/tmp/idle-worker.log"
LOCK_DIR="/tmp/idle-worker.lock.d"
IDLE_THRESHOLD=1800  # 30 минут в секундах
MAX_TASK_TIME=1800   # 30 минут на задачу
LOCK_STALE=3600      # 1 час — stale lock cleanup
CACHE_DIR="/tmp/idle-worker-cache"
CACHE_TTL=900        # 15 минут — кэш Asana ответа

# Лог с ротацией (макс 5MB)
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 5242880 ]; then
    mv "$LOG" "${LOG}.old"
fi

# === GATE 1: ioreg idle check (cheapest, ~2ms) ===
# Do this BEFORE lock acquisition to avoid mkdir/rmdir overhead on active systems
IDLE_SEC=$(ioreg -c IOHIDSystem 2>/dev/null | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
IDLE_SEC="${IDLE_SEC:-0}"

if [ "$IDLE_SEC" -lt "$IDLE_THRESHOLD" ]; then
    exit 0  # пользователь активен — выходим мгновенно, без лока
fi

# === GATE 2: lock (only reached when idle) ===
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        exit 0  # уже работает
    fi
    # Stale lock check — если lock старше LOCK_STALE секунд
    LOCK_AGE=$(( $(date +%s) - $(stat -f%m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$LOCK_AGE" -lt "$LOCK_STALE" ]; then
        exit 0  # lock свежий, но PID мёртв — подождём
    fi
    log "Removing stale lock (age: ${LOCK_AGE}s, dead PID: ${LOCK_PID})"
    rm -rf "$LOCK_DIR"
    mkdir "$LOCK_DIR" || exit 0
fi
echo $$ > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT

# === GATE 3: check active Claude sessions ===
CLAUDE_ACTIVE=$(pgrep -x "claude" 2>/dev/null | wc -l | tr -d ' ')
if [ "$CLAUDE_ACTIVE" -gt 0 ]; then
    # Claude process exists — check if it's a recent interactive session
    if find ~/.claude/projects/ -name "*.jsonl" -mmin -30 2>/dev/null | head -1 | grep -q .; then
        exit 0  # активная сессия < 30 мин
    fi
fi

log "=== IDLE DETECTED (${IDLE_SEC}s) — starting task picker ==="

# === Asana cache setup ===
mkdir -p "$CACHE_DIR"
CACHE_FILE="$CACHE_DIR/tasks.json"
CACHE_META="$CACHE_DIR/tasks.meta"
TASK_INFO_FILE=$(mktemp /tmp/idle-worker-taskinfo-XXXXXX.txt)
chmod 600 "$TASK_INFO_FILE"

# === Task picker (Python) with Asana caching ===
TASK_INFO_FILE_EXPORT="$TASK_INFO_FILE" \
CACHE_FILE_EXPORT="$CACHE_FILE" \
CACHE_META_EXPORT="$CACHE_META" \
CACHE_TTL_EXPORT="$CACHE_TTL" \
python3 << 'PYEOF'
import json
import os
import re
import sys
import time
from datetime import date, timedelta

ASANA_PAT = os.environ.get("ASANA_PAT", "")
if not ASANA_PAT:
    tokens_path = os.path.expanduser("~/artvision-data/tokens.json")
    if os.path.exists(tokens_path):
        with open(tokens_path) as f:
            ASANA_PAT = json.load(f).get("asana", {}).get("pat", "")

if not ASANA_PAT:
    print("No ASANA_PAT found", file=sys.stderr)
    sys.exit(1)

PROJECT_GID = "1212305892582815"

# --- Asana response caching ---
cache_file = os.environ.get("CACHE_FILE_EXPORT", "/tmp/idle-worker-cache/tasks.json")
cache_meta = os.environ.get("CACHE_META_EXPORT", "/tmp/idle-worker-cache/tasks.meta")
cache_ttl = int(os.environ.get("CACHE_TTL_EXPORT", "900"))

tasks = None
now = time.time()

# Try cache first
if os.path.exists(cache_file) and os.path.exists(cache_meta):
    try:
        with open(cache_meta) as f:
            cached_at = float(f.read().strip())
        if now - cached_at < cache_ttl:
            with open(cache_file) as f:
                tasks = json.load(f)
            print(f"Using cached tasks ({int(now - cached_at)}s old)", file=sys.stderr)
    except (ValueError, json.JSONDecodeError, OSError):
        pass  # cache corrupt, refetch

# Fetch from API if no valid cache
if tasks is None:
    import urllib.request
    url = f"https://app.asana.com/api/1.0/projects/{PROJECT_GID}/tasks?opt_fields=name,due_on,completed,assignee.name,notes&limit=50"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {ASANA_PAT}",
        "Accept": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            tasks = json.loads(resp.read())["data"]
    except Exception as e:
        print(f"Asana API error: {e}", file=sys.stderr)
        sys.exit(1)

    # Write cache atomically
    tmp_cache = cache_file + ".tmp"
    with open(tmp_cache, "w") as f:
        json.dump(tasks, f)
    os.replace(tmp_cache, cache_file)
    with open(cache_meta, "w") as f:
        f.write(str(now))

# --- Task filtering and sorting ---
open_tasks = [t for t in tasks if not t.get("completed")]

if not open_tasks:
    print("No open tasks")
    sys.exit(0)

today = date.today().isoformat()
soon = (date.today() + timedelta(days=3)).isoformat()

def sort_key(task):
    due = task.get("due_on") or "9999-12-31"
    if due < today:
        return (0, due)
    elif due == today:
        return (1, due)
    elif due <= soon:
        return (2, due)
    return (3, due)

open_tasks.sort(key=sort_key)

SAFE_PATTERNS = [
    "аудит", "анализ", "research", "исследование", "документ", "review",
    "refactor", "написать код", "создать скрипт", "обновить", "подготовить",
    "seo", "контент", "статья", "парсинг", "мониторинг", "отчёт",
    "скрипт", "тест", "fix", "баг", "оптимизация", "план", "roadmap",
]

BLOCK_PATTERNS = [
    "клиент", "отправить", "позвонить", "написать клиенту", "опубликовать",
    "деплой на прод", "push to prod", "рассылка", "email клиенту",
    "счёт", "оплата", "NDA", "удалить", "drop", "rm -rf", "delete prod",
]

def sanitize(text, max_len=500):
    text = text[:max_len]
    # Strip prompt injection attempts
    text = re.sub(r'(?i)(ignore|forget|disregard|override|bypass|run:|exec:|sudo|rm\s+-rf|<system|</system|<tool|</tool|allowedTools|--allow).*', '[REDACTED]', text)
    # Remove shell metacharacters
    text = re.sub(r'[;|&`$(){}\\<>]', '', text)
    return text

def validate_gid(gid):
    """Validate Asana GID format (numeric, 10-20 digits)"""
    return bool(re.match(r'^\d{10,20}$', str(gid)))

auto_tasks = []
for task in open_tasks:
    name = (task.get("name") or "").lower()
    notes = (task.get("notes") or "").lower()
    combined = name + " " + notes
    if any(kw in combined for kw in BLOCK_PATTERNS):
        continue
    if not any(kw in combined for kw in SAFE_PATTERNS):
        continue
    auto_tasks.append(task)

if not auto_tasks:
    print("No AUTO-level tasks available")
    sys.exit(0)

task = auto_tasks[0]
task_gid = task.get("gid", "")
if not validate_gid(task_gid):
    print(f"Invalid GID format: {task_gid}", file=sys.stderr)
    sys.exit(1)
task_name = sanitize(task.get("name", "Unknown"), 200)
task_notes = sanitize(task.get("notes", ""), 500)
task_due = task.get("due_on", "no deadline")

print(f"PICKED: [{task_gid}] {task_name} (due: {task_due})")

# Write task info (name + gid) and prompt to the info file
info_file = os.environ.get("TASK_INFO_FILE_EXPORT", "/tmp/idle-worker-taskinfo.txt")
prompt = f"""Ты — автономный idle-worker. Выполни задачу из Asana.

ЗАДАЧА: {task_name}
ДЕДЛАЙН: {task_due}
ОПИСАНИЕ: {task_notes}
ASANA GID: {task_gid}

СТРОГИЕ ПРАВИЛА:
1. Только безопасные действия: код, документы, аудиты, анализ, скрипты
2. ЗАПРЕЩЕНО: отправлять сообщения клиентам, публиковать, деплоить на прод, удалять данные
3. У тебя НЕТ Bash/терминала. Только Read/Write/Edit/Glob/Grep
4. Записать что сделано в /tmp/idle-worker-result.md
5. Таймаут: 30 минут максимум
"""

fd = os.open(info_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    # Line 1: task name for notifications
    # Line 2: task gid
    # Line 3+: prompt
    f.write(f"TASK_NAME={task_name}\n")
    f.write(f"TASK_GID={task_gid}\n")
    f.write(f"---\n")
    f.write(prompt)
PYEOF

# 4. Если picker нашёл задачу — запустить Claude
if [ -f "$TASK_INFO_FILE" ] && [ -s "$TASK_INFO_FILE" ]; then
    # Extract task name for notifications (line 1)
    TASK_NAME=$(head -1 "$TASK_INFO_FILE" | sed 's/^TASK_NAME=//')
    # Extract prompt (everything after ---\n)
    PROMPT=$(sed '1,/^---$/d' "$TASK_INFO_FILE")

    if [ -n "$PROMPT" ]; then
        log "Executing task: $TASK_NAME"

        # Run in foreground — timeout already handles kill
        # SECURITY: NO Bash tool — prevents RCE via Asana task injection
        # Claude can only read/write/search files, not execute commands
        # macOS: use gtimeout (coreutils) or bash fallback
        CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude 2>/dev/null || echo /Users/antonk/.local/bin/claude)}"
        if command -v gtimeout &>/dev/null; then
            gtimeout "$MAX_TASK_TIME" "$CLAUDE_BIN" -p "$PROMPT" \
                --allowedTools "Read,Write,Edit,Glob,Grep" \
                --model sonnet \
                >> "$LOG" 2>&1 || log "Executor finished with code $?"
        else
            "$CLAUDE_BIN" -p "$PROMPT" \
                --allowedTools "Read,Write,Edit,Glob,Grep" \
                --model sonnet \
                >> "$LOG" 2>&1 &
            CLAUDE_PID=$!
            ( sleep "$MAX_TASK_TIME" && kill "$CLAUDE_PID" 2>/dev/null ) &
            TIMER_PID=$!
            wait "$CLAUDE_PID" 2>/dev/null || log "Executor finished with code $?"
            kill "$TIMER_PID" 2>/dev/null
        fi

        # Проверка результата
        if [ -f /tmp/idle-worker-result.md ]; then
            LINES=$(wc -l < /tmp/idle-worker-result.md | tr -d ' ')
            log "Result: $LINES lines written"
            if [ -x ~/.claude/scripts/send-tg.sh ]; then
                ~/.claude/scripts/send-tg.sh "Idle Worker completed: $TASK_NAME ($LINES lines)" 2>/dev/null || true
            fi
        else
            log "WARNING: No result file produced"
        fi

        log "=== Task execution complete ==="
    fi
fi

rm -f "$TASK_INFO_FILE"
