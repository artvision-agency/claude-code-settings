#!/usr/bin/env python3
"""
Session Auto-Logger for Claude Code
Сохраняет важные уроки из сессий в лог-файл
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".claude" / "session_logs"
LOG_FILE = LOG_DIR / "lessons_learned.md"

def ensure_log_dir():
    """Создаёт директорию для логов если её нет"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("""# Claude Session Lessons Learned

Автоматически собранные уроки из сессий.

---

""")

def append_lesson(lesson: dict):
    """Добавляет урок в лог-файл"""
    ensure_log_dir()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    cwd = lesson.get("cwd", "unknown")
    category = lesson.get("category", "general")
    description = lesson.get("description", "")
    action = lesson.get("action", "")

    entry = f"""## [{timestamp}] {category}

**Проект:** `{cwd}`

**Что произошло:** {description}

**Урок/Действие:** {action}

---

"""

    with open(LOG_FILE, "a") as f:
        f.write(entry)

    print(f"✅ Урок записан в {LOG_FILE}")

def main():
    """Основная функция — принимает JSON с данными урока"""
    if len(sys.argv) < 2:
        # Если вызван без аргументов — показать справку
        print("""
Использование: save_session.py '<json>'

JSON формат:
{
    "category": "error|pattern|decision|optimization",
    "description": "Что произошло",
    "action": "Что нужно помнить/делать",
    "cwd": "/path/to/project"
}

Пример:
save_session.py '{"category": "error", "description": "Прочитал огромный файл", "action": "Использовать Grep для файлов >5K строк"}'
""")
        return

    try:
        lesson = json.loads(sys.argv[1])
        append_lesson(lesson)
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
