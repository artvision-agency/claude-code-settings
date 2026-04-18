#!/bin/bash
set -euo pipefail
# Context Bridge: синхронизация контекста между TG-ботом и Claude Code
# Собирает состояние Claude Code → SHARED_CONTEXT.md → git push
# Использование: вызывать при Stop сессии и по cron каждые 30 мин
# Также может вызываться TG-ботом через git pull

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

ARTVISION_DATA="$HOME/artvision-data"
SHARED_CONTEXT="$ARTVISION_DATA/sync/SHARED_CONTEXT.md"
SESSION_STATE="$ARTVISION_DATA/sync/SESSION_STATE.json"
LOCK_FILE="/tmp/context-bridge.lock"

# flock to prevent concurrent runs
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "Another context-bridge instance is running, exiting."
    exit 0
fi

NOW=$(date "+%Y-%m-%d %H:%M")

mkdir -p "$(dirname "$SHARED_CONTEXT")"

# Git pull first to avoid stale context / push conflicts
cd "$ARTVISION_DATA"
git pull --rebase --quiet 2>/dev/null || echo "[WARN] git pull failed, continuing with local state" >&2

# ═══════════════════════════════════════════════
# Сбор данных через Python (безопасный вывод)
# ═══════════════════════════════════════════════

python3 << 'PYEOF' || { echo "[ERROR] Python data collection failed" >&2; }
import json, subprocess, os, re
from datetime import datetime, timedelta
from pathlib import Path

HOME = os.path.expanduser("~")
ARTVISION_DATA = os.path.join(HOME, "artvision-data")
SHARED_CONTEXT = os.path.join(ARTVISION_DATA, "sync/SHARED_CONTEXT.md")
SESSION_STATE = os.path.join(ARTVISION_DATA, "sync/SESSION_STATE.json")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# --- 1. Последние 5 коммитов из artvision-data ---
try:
    commits_raw = subprocess.check_output(
        ["git", "log", "--oneline", "--no-merges", "-5",
         "--format=%h|%s|%ar|%an"],
        cwd=ARTVISION_DATA, stderr=subprocess.DEVNULL
    ).decode().strip().split("\n")
except Exception:
    commits_raw = []

commits = []
for line in commits_raw:
    if not line.strip():
        continue
    parts = line.split("|", 3)
    if len(parts) >= 3:
        commits.append({
            "hash": parts[0],
            "msg": parts[1],
            "when": parts[2],
            "author": parts[3] if len(parts) > 3 else ""
        })

# --- 2. Активные клиенты (по git log за 24ч) ---
try:
    since_24h = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d")
    changed_files = subprocess.check_output(
        ["git", "log", "--since", since_24h, "--name-only",
         "--pretty=format:", "--no-merges"],
        cwd=ARTVISION_DATA, stderr=subprocess.DEVNULL
    ).decode().strip().split("\n")
except Exception:
    changed_files = []

# Извлечь клиентов из путей clients/NAME/...
active_clients = set()
active_products = set()
for f in changed_files:
    f = f.strip()
    if not f:
        continue
    if f.startswith("clients/"):
        parts = f.split("/")
        if len(parts) >= 2:
            active_clients.add(parts[1])
    elif f.startswith("products/"):
        parts = f.split("/")
        if len(parts) >= 2:
            active_products.add(parts[1])

# --- 3. Открытые задачи из TODO.md ---
TODO_FILES = [
    os.path.join(ARTVISION_DATA, "TODO.md"),
    os.path.join(HOME, "artvision-tg-bot/TODO.md"),
    os.path.join(ARTVISION_DATA, "presale/TODO.md"),
    os.path.join(ARTVISION_DATA, "products/TODO.md"),
]

pending_tasks = []
pattern = re.compile(r'^\s*- \[ \] \*{0,2}(.+?)\*{0,2}\s*$')
for todo_file in TODO_FILES:
    if not os.path.isfile(todo_file):
        continue
    context = os.path.basename(os.path.dirname(todo_file))
    try:
        with open(todo_file, "r") as f:
            for line in f:
                m = pattern.match(line)
                if m:
                    task = m.group(1).strip()
                    # Убрать markdown bold
                    task = task.replace("**", "")
                    if task and len(pending_tasks) < 15:
                        pending_tasks.append(f"[{context}] {task[:120]}")
    except Exception:
        continue

# --- 4. Данные из SESSION_STATE.json (последняя сессия) ---
session_info = {}
if os.path.isfile(SESSION_STATE):
    try:
        with open(SESSION_STATE, "r") as f:
            session_info = json.load(f)
    except Exception:
        pass

session_time = session_info.get("timestamp", "неизвестно")
session_duration = session_info.get("session_duration_min", 0)
session_account = session_info.get("account", "неизвестно")
session_dir = session_info.get("current_dir", "")

# --- 5. Последние TG-сообщения (из voice_inbox если есть) ---
tg_messages = []
voice_processed = os.path.join(HOME, ".claude_temp_scripts/voice_processed.txt")
voice_log = os.path.join(HOME, ".claude_temp_scripts/voice_log.txt")

# Проверяем лог голосовых (если ведётся)
for log_file in [voice_log, voice_processed]:
    if os.path.isfile(log_file):
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()[-5:]  # последние 5
                for line in lines:
                    line = line.strip()
                    if line:
                        tg_messages.append(line)
        except Exception:
            pass

# Также проверяем client-tg-messages.md
tg_msgs_file = os.path.join(ARTVISION_DATA, "sync/client-tg-messages.md")
if os.path.isfile(tg_msgs_file):
    try:
        with open(tg_msgs_file, "r") as f:
            content = f.read()
        # Берём последние 5 строк с сообщениями
        for line in content.split("\n")[-10:]:
            line = line.strip()
            if line and not line.startswith("#") and line not in tg_messages:
                tg_messages.append(line[:150])
                if len(tg_messages) >= 5:
                    break
    except Exception:
        pass

# --- 6. Определить фокус ---
focus_client = ""
focus_product = ""

if active_clients:
    # Клиент с наибольшим количеством изменений
    client_counts = {}
    for f in changed_files:
        f = f.strip()
        if f.startswith("clients/"):
            parts = f.split("/")
            if len(parts) >= 2:
                name = parts[1]
                client_counts[name] = client_counts.get(name, 0) + 1
    if client_counts:
        focus_client = max(client_counts, key=client_counts.get)

if active_products:
    focus_product = sorted(active_products)[0]

# --- 7. Блокеры (из TODO — строки с СРОЧНО/ПРОСРОЧЕНО/блокер) ---
blockers = []
blocker_keywords = ["срочно", "просрочено", "блокер", "blocker", "critical", "broken"]
for task in pending_tasks:
    task_lower = task.lower()
    if any(kw in task_lower for kw in blocker_keywords):
        blockers.append(task)

# ═══════════════════════════════════════════════
# Генерация SHARED_CONTEXT.md
# ═══════════════════════════════════════════════

lines = []
lines.append(f"# Shared Context -- {NOW}")
lines.append(f"Автообновление: при Stop сессии Claude Code + cron каждые 30 мин")
lines.append("")

# Последняя сессия
lines.append("## Последняя сессия Claude Code")
lines.append(f"- Время: {session_time}")
if session_duration:
    lines.append(f"- Длительность: ~{session_duration} мин")
lines.append(f"- Аккаунт: {session_account}")
if session_dir:
    lines.append(f"- Рабочая директория: {session_dir}")
lines.append("")

# Последние коммиты
lines.append("## Последние коммиты")
if commits:
    for c in commits:
        # Пропускаем sync коммиты
        if c["msg"].startswith("sync: session state"):
            continue
        lines.append(f"- `{c['hash']}` {c['msg']} ({c['when']})")
else:
    lines.append("- Нет коммитов за последние 24ч")
lines.append("")

# Активные клиенты/продукты
lines.append("## Работали за последние 24ч")
if active_clients:
    lines.append(f"- Клиенты: {', '.join(sorted(active_clients))}")
if active_products:
    lines.append(f"- Продукты: {', '.join(sorted(active_products))}")
if not active_clients and not active_products:
    lines.append("- Нет изменений в клиентских/продуктовых файлах")
lines.append("")

# Открытые задачи (топ-10)
lines.append("## Открытые задачи (топ-15)")
if pending_tasks:
    for task in pending_tasks[:15]:
        lines.append(f"- {task}")
else:
    lines.append("- Нет открытых задач")
lines.append("")

# TG-сообщения
lines.append("## Последние TG-сообщения")
if tg_messages:
    for msg in tg_messages[-5:]:
        lines.append(f"- {msg}")
else:
    lines.append("- Нет недавних сообщений")
lines.append("")

# Активный контекст
lines.append("## Активный контекст")
lines.append(f"- Клиент в фокусе: {focus_client or 'не определён'}")
lines.append(f"- Продукт в фокусе: {focus_product or 'не определён'}")
if blockers:
    lines.append("- Блокеры:")
    for b in blockers:
        lines.append(f"  - {b}")
else:
    lines.append("- Блокеры: нет")
lines.append("")

# JSON-версия для программного чтения ботом
lines.append("<!-- JSON_START")
json_data = {
    "updated": NOW,
    "session_time": session_time,
    "session_account": session_account,
    "focus_client": focus_client,
    "focus_product": focus_product,
    "active_clients": sorted(active_clients),
    "active_products": sorted(active_products),
    "pending_tasks_count": len(pending_tasks),
    "top_tasks": pending_tasks[:10],
    "blockers": blockers,
    "last_commits": [c["msg"] for c in commits if not c["msg"].startswith("sync: session state")][:5],
}
lines.append(json.dumps(json_data, ensure_ascii=False, indent=2))
lines.append("JSON_END -->")

with open(SHARED_CONTEXT, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"SHARED_CONTEXT.md updated: {NOW}")
print(f"  Clients: {', '.join(sorted(active_clients)) or 'none'}")
print(f"  Tasks: {len(pending_tasks)}")
print(f"  Blockers: {len(blockers)}")
PYEOF

# ═══════════════════════════════════════════════
# Git commit + push (если есть изменения)
# ═══════════════════════════════════════════════

# Already cd'd to ARTVISION_DATA above

if [ -n "$(git diff --name-only sync/SHARED_CONTEXT.md 2>/dev/null)" ] || \
   [ -n "$(git ls-files --others --exclude-standard sync/SHARED_CONTEXT.md 2>/dev/null)" ]; then
    git add sync/SHARED_CONTEXT.md
    git commit -m "sync: update shared context ${NOW}

Co-Authored-By: Claude <noreply@anthropic.com>" --quiet 2>/dev/null || true
    if ! git push --quiet 2>/dev/null; then
        echo "[WARN] git push failed for SHARED_CONTEXT.md" >> /tmp/context-bridge-errors.log
        echo "Git: committed but push FAILED (logged to /tmp/context-bridge-errors.log)"
    else
        echo "Git: committed and pushed SHARED_CONTEXT.md"
    fi
else
    echo "Git: no changes to SHARED_CONTEXT.md"
fi
