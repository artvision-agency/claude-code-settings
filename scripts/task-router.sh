#!/bin/bash
set -euo pipefail

# Task Router — маршрутизация задач между сессиями Claude Code
# Запуск: каждые 30 мин через cron или вручную
# Логика: читает TODO.md всех сессий → проверяет принадлежность → перекидывает

CONFIG="$HOME/.claude/task-router/sessions.yaml"
INBOX_DIR="$HOME/.claude/task-router/inbox"
LOG="$HOME/.claude/task-router/router.log"
LOCK="$HOME/.claude/task-router/router.lock"
DRY_RUN="${1:-}"  # --dry-run для тестирования

mkdir -p "$INBOX_DIR"

# Lock file: предотвращает параллельный запуск (race condition от cron)
cleanup_lock() {
    rm -f "$LOCK"
}
trap cleanup_lock EXIT

if [ -f "$LOCK" ]; then
    # Проверяем не завис ли предыдущий процесс (>10 мин = stale lock)
    if [ "$(uname)" = "Darwin" ]; then
        lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK") ))
    else
        lock_age=$(( $(date +%s) - $(stat -c %Y "$LOCK") ))
    fi
    if [ "$lock_age" -lt 600 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Router: другой процесс уже работает (lock age: ${lock_age}s)" >> "$LOG"
        exit 0
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Router: stale lock (${lock_age}s), переписываю" >> "$LOG"
fi
echo $$ > "$LOCK"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

# Парсинг sessions.yaml через python (надёжнее чем yq для вложенных структур)
python3 - "$DRY_RUN" << 'PYEOF'
import yaml
import re
import os
import sys
from datetime import datetime
from pathlib import Path

CONFIG = os.path.expanduser("~/.claude/task-router/sessions.yaml")
INBOX_DIR = os.path.expanduser("~/.claude/task-router/inbox")
LOG = os.path.expanduser("~/.claude/task-router/router.log")
DRY_RUN = "--dry-run" in sys.argv

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

# Загрузить конфиг
with open(CONFIG) as f:
    config = yaml.safe_load(f)

sessions = config.get("sessions", {})

# Собрать все задачи из всех TODO.md
all_tasks = {}  # {todo_file: [(line_num, task_text, is_done)]}
for name, sess in sessions.items():
    todo = sess.get("todo_file", "")
    if todo and os.path.exists(todo):
        with open(todo) as f:
            lines = f.readlines()
        tasks = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Ищем задачи формата - [ ] или - [x]
            m = re.match(r'^-\s*\[([ x])\]\s*(.*)', stripped)
            if m:
                done = m.group(1) == 'x'
                text = m.group(2).strip()
                tasks.append((i, text, done, line))
        all_tasks[todo] = tasks

# Для каждой задачи — определить правильную сессию
def score_task(task_text, session_name, session_config):
    """Считает совпадения задачи с ключевыми словами сессии"""
    keywords = session_config.get("keywords", [])
    text_lower = task_text.lower()
    score = 0
    matched = []

    # Проверка принудительной метки [session:xxx]
    forced = re.search(r'\[session:(\S+)\]', task_text)
    if forced:
        if forced.group(1) == session_name:
            return 1000, ["forced"]
        else:
            return -1, []

    for kw in keywords:
        if kw.lower() in text_lower:
            score += 1
            matched.append(kw)

    return score, matched

moves = []  # (task_text, from_file, to_file, to_session, score, keywords, line_num)

for source_file, tasks in all_tasks.items():
    # Какая сессия владеет этим TODO?
    source_session = None
    for name, sess in sessions.items():
        if sess.get("todo_file") == source_file:
            source_session = name
            break

    if not source_session:
        continue

    for line_num, task_text, is_done, raw_line in tasks:
        if is_done:
            continue  # Не трогаем завершённые

        # Пропускаем задачи с [routed] — они уже перемещены, не пинг-понгить
        if '[routed]' in task_text:
            continue

        # Считаем score для каждой сессии
        best_session = source_session
        best_score = 0
        best_keywords = []
        source_score = 0

        for name, sess in sessions.items():
            score, matched = score_task(task_text, name, sess)
            if name == source_session:
                source_score = score
            if score > best_score:
                best_score = score
                best_session = name
                best_keywords = matched

        # Перемещаем только если:
        # 1. Лучшая сессия != текущая
        # 2. Score лучшей > score текущей + 1 (порог чтобы не дёргать задачи)
        if best_session != source_session and best_score > source_score + 1:
            target_file = sessions[best_session].get("todo_file", "")
            if target_file:
                moves.append((task_text, source_file, target_file, best_session, best_score, best_keywords, line_num))

# Отчёт
if not moves:
    log("Router: все задачи на месте, перемещений нет")
    print("✅ Все задачи на месте")
    sys.exit(0)

print(f"{'[DRY RUN] ' if DRY_RUN else ''}Найдено {len(moves)} задач для перемещения:\n")

for task_text, src, dst, sess_name, score, kws, lnum in moves:
    src_short = os.path.basename(os.path.dirname(src)) + "/" + os.path.basename(src)
    dst_short = os.path.basename(os.path.dirname(dst)) + "/" + os.path.basename(dst)
    suffix = "..." if len(task_text) > 60 else ""
    print(f"  {task_text[:60]}{suffix}")
    print(f"     {src_short} → {dst_short} ({sess_name}, score={score}, keywords={kws})")
    print()

if DRY_RUN:
    log(f"Router DRY RUN: {len(moves)} задач для перемещения")
    sys.exit(0)

# Выполняем перемещения
# Группируем по source и target для batch-обработки
from collections import defaultdict
import tempfile, shutil

removals = defaultdict(set)    # {source_file: {line_num, ...}}
additions = defaultdict(list)  # {target_file: [task_text]}

for task_text, src, dst, sess_name, score, kws, lnum in moves:
    removals[src].add(lnum)
    additions[dst].append(f"- [ ] **[routed]** {task_text}\n")

# Сначала добавляем в target (если упадём — лучше дубль чем потеря)
for dst_file, new_tasks in additions.items():
    if os.path.exists(dst_file):
        with open(dst_file) as f:
            content = f.read()

        # Ищем секцию "В работе" или "## В работе"
        insert_marker = None
        for marker in ["## В работе\n", "### В работе\n", "## Pending\n"]:
            if marker in content:
                insert_marker = marker
                break

        if insert_marker:
            parts = content.split(insert_marker, 1)
            lines_after = parts[1].split("\n")
            # Находим ПОСЛЕДНЮЮ строку с задачей в этой секции, вставляем ПОСЛЕ неё
            insert_pos = 0
            for i, line in enumerate(lines_after):
                if line.strip().startswith("- ["):
                    insert_pos = i + 1  # после последней найденной задачи
                elif line.strip().startswith("##"):
                    break  # дошли до следующей секции — стоп
                elif not line.strip() and insert_pos == 0:
                    insert_pos = i + 1  # пустая строка после заголовка

            task_lines = [t.rstrip('\n') for t in new_tasks]
            lines_after[insert_pos:insert_pos] = task_lines
            content = parts[0] + insert_marker + "\n".join(lines_after)
        else:
            # Добавляем в конец с отдельной секцией
            content += "\n### Входящие (routed)\n" + "".join(new_tasks)

        # Атомарная запись через tmpfile + rename (защита от crash mid-write)
        dir_name = os.path.dirname(dst_file)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            shutil.move(tmp_path, dst_file)
        except:
            os.unlink(tmp_path)
            raise
    else:
        # Создаём новый TODO
        with open(dst_file, "w") as f:
            f.write("# TODO\n\n## В работе\n\n")
            f.writelines(new_tasks)

# Потом удаляем из source (по номерам строк — точное удаление)
for src_file, line_nums in removals.items():
    with open(src_file) as f:
        content = f.readlines()
    new_content = [l for i, l in enumerate(content) if i not in line_nums]
    # Атомарная запись
    dir_name = os.path.dirname(src_file)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.writelines(new_content)
        shutil.move(tmp_path, src_file)
    except:
        os.unlink(tmp_path)
        raise

# Записываем в inbox для уведомления сессий
for dst_file, new_tasks in additions.items():
    # Находим имя сессии
    for name, sess in sessions.items():
        if sess.get("todo_file") == dst_file:
            inbox_file = os.path.join(INBOX_DIR, f"{name}.md")
            with open(inbox_file, "a") as f:
                f.write(f"\n## Routed {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.writelines(new_tasks)
            break

log(f"Router: перемещено {len(moves)} задач")
print(f"\n✅ Перемещено {len(moves)} задач")
PYEOF
