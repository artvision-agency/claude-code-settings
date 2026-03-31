---
name: project-audit
description: Use when setting up Claude Code infrastructure for a project — audits and creates missing rules, templates, hooks, skills, architecture decisions, and archives stale memory. Use when starting a new project, onboarding to existing one, or when user says "audit", "set up .claude", "create hooks", "project structure"
---

# Project Audit

Аудит и настройка инфраструктуры Claude Code по best practices.

## Overview

Анализирует `.claude/` структуру проекта и создаёт недостающее: обязательные skills, rules, templates, hooks, architecture decisions, review workflow. Упрощает CLAUDE.md если раздут.

## When to Use

- Новый проект без `.claude/` инфраструктуры
- Существующий проект — хочется навести порядок
- Пользователь говорит "аудит", "настрой .claude", "создай хуки"

## Audit Checklist

Выполняй **строго по порядку**. Каждый шаг — отдельная задача в TaskCreate.

### Step 1: Анализ текущего состояния

Проверить наличие и содержимое:

```
.claude/
  skills/         — есть ли обязательные (tdd, solid-dry-kiss, ddd-hexagonal)?
  rules/          — есть? покрывают ли стиль, профиль, архитектуру?
  templates/      — есть? шаблоны под стек проекта?
  scripts/        — есть? hooks подключены в settings?
  agents/         — есть? субагентные инструкции?
CLAUDE.md         — сколько строк? (>200 = раздут) Есть ли секция Architecture & Methodology?
memory/           — сколько файлов? есть ли устаревшие? есть ли feedback-review-workflow?
settings.local.json — hooks подключены?
scripts/sync-skills.sh — синхронизация skills настроена?
```

Вывести таблицу: что есть ✅, чего нет ❌, что требует улучшения ⚠️.

### Step 2: Обязательные Skills

Три skill'а ОБЯЗАТЕЛЬНЫ в каждом проекте (`.claude/skills/`):

| Skill | Назначение |
|-------|-----------|
| **tdd** | RED-GREEN-REFACTOR, тесты перед кодом |
| **solid-dry-kiss** | SOLID, DRY, KISS, YAGNI принципы |
| **ddd-hexagonal** | Domain-Driven Design + Hexagonal Architecture |

Для каждого отсутствующего:
1. Проверить в `~/claude-code-settings/skills/` (источник)
2. Если есть — скопировать в `.claude/skills/`
3. Если нет — создать минимальный skill

**По стеку проекта** — подключить дополнительные:
- Python → `python-testing-patterns`
- aiogram → `aiogram-patterns`
- React/TS → `react-best-practices`
- SQLAlchemy async → `sqlalchemy-async`

### Step 3: Синхронизация Skills

Шаблон скрипта: `~/claude-code-settings/scripts/sync-skills-template.sh`

Настройка:
1. Скопировать шаблон в `scripts/sync-skills.sh` проекта
2. Изменить `PROJECT_DIR`, `SOURCE_REPO`, `SKILLS` под проект
3. `chmod +x scripts/sync-skills.sh`
4. Добавить в cron: `crontab -e`

Логика скрипта:
- `git pull` source repo (claude-code-settings)
- Хеш по содержимому файлов (не по путям) — `find | sort | xargs cat | md5sum`
- Source изменился → `rsync -a --delete source/ target/` (обновить проект)
- Проект изменился → `rsync -a --delete target/ source/` + git push
- Оба изменились → **CONFLICT** → уведомление в Telegram (BOT_TOKEN + CHAT_ID из .env)
- Хеши хранятся в `data/.skills-hashes/`

Cron (ежедневно в 6:00 UTC):
```
0 6 * * * /path/to/scripts/sync-skills.sh >> data/logs/sync-skills.log 2>&1
```

**Важно:** НЕ использовать `cp -r` для синхронизации — создаёт вложенные копии. Только `rsync -a --delete` с trailing slash.

### Step 4: Hooks (максимальный эффект)

Создать `.claude/scripts/` с тремя хуками:

**hook-post-commit.sh** — напоминание после `git commit`:
- Обновить memory/docs
- Нужен ли deploy
- Нужен ли git push

**hook-pre-deploy.sh** — блокировка деплоя:
- Проверка непушнутых коммитов (exit 2 если есть)
- Warning о незакоммиченных изменениях
- Адаптировать команду деплоя под проект

**hook-stop-reminder.sh** — чеклист завершения сессии:
- Memory обновлена?
- Тесты проходят?
- Коммит/push сделан?
- Deploy нужен?

Подключить в `settings.local.json`:
```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash .claude/scripts/hook-pre-deploy.sh"}]}],
    "PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash .claude/scripts/hook-post-commit.sh"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "bash .claude/scripts/hook-stop-reminder.sh"}]}]
  }
}
```

### Step 5: Rules

Создать `.claude/rules/` — вынести из CLAUDE.md пассивный контекст:

**coding-style.md** (globs: `["**/*.{py,ts,js,go}"]`):
- Логирование (формат, библиотека)
- DB-паттерны (ORM, сессии, миграции)
- Специфичные gotchas проекта

**profile.md** (globs: `["**/*"]`):
- Язык общения
- Уровень автономности
- Что НЕ делать без спроса

**architecture.md** (globs: `["**/*.{py,ts,js,go}"]`):
- Ключевые архитектурные паттерны
- Ссылки на templates

### Step 6: CLAUDE.md — Architecture & Methodology

Проверить что CLAUDE.md содержит секцию:

```markdown
## Architecture & Methodology
- **TDD**: сначала тесты (RED), потом код (GREEN), потом рефакторинг
- **SOLID/DRY/KISS**: `.claude/skills/solid-dry-kiss/SKILL.md`
- **DDD + Hexagonal**: `.claude/skills/ddd-hexagonal/SKILL.md`
- Бизнес-логика → `domain/` или `application/` (use cases)
- `webapp/server.py`, `bot/handlers/` — только тонкие адаптеры
- При запуске субагентов ВСЕГДА передавать эти требования в промпт
```

Если нет — добавить. Если CLAUDE.md > 100 строк — вынести детали в rules.

Целевой размер: **60-90 строк**.

### Step 7: Review Workflow (memory)

Проверить что в memory есть `feedback-review-workflow.md`:

```
После выполнения каждой задачи:
1. /aif-verify — проверить что код работает
2. /aif-review — code review
3. /aif-fix — исправить criticals + importants
4. /aif-review — повторный ревью
5. Показать пользователю результат: criticals, importants, suggestions, вопросы
6. Ждать решения пользователя
```

Также проверить `feedback-agents-ddd-tdd.md`:
```
При запуске субагентов ВСЕГДА передавать:
1. TDD: прочитай .claude/skills/tdd/SKILL.md
2. SOLID/DRY/KISS: прочитай .claude/skills/solid-dry-kiss/SKILL.md
3. DDD + Hexagonal: прочитай .claude/skills/ddd-hexagonal/SKILL.md
```

### Step 8: Templates

Создать `.claude/templates/` — шаблоны по стеку проекта:
- **Python web**: новый эндпоинт, миграция, модель, тест
- **React/TS**: новый компонент, страница, хук
- **Bot (aiogram)**: новый хендлер, FSM, клавиатура
- **Scraper**: новый парсер сайта
- **General**: новый канал/ресурс

Каждый шаблон: скелет файла + чеклист + где зарегистрировать.

### Step 9: Architecture Decisions

Создать `memory/architecture-decisions.md` если нет.

Формат ADR:
```markdown
## ADR-NNN: Название
**Решение**: что выбрали
**Причина**: почему
**Отвергнуто**: что рассматривали и почему отказались
**Дата**: YYYY-MM-DD
```

### Step 10: Архивирование memory

- Проверить каждый memory-файл на актуальность
- Устаревшие → `memory/archive/`
- Обновить MEMORY.md — убрать мёртвые ссылки
- Целевой размер MEMORY.md: **< 100 строк**

## Common Mistakes

| Ошибка | Исправление |
|--------|-------------|
| Нет обязательных skills | Субагенты не следуют TDD/DDD/SOLID |
| Skills только глобально (~/.claude/) | Субагенты в worktree не видят — копировать в проект |
| Нет синхронизации skills | Обновления из git не попадают в проект |
| Всё в CLAUDE.md | Rules/templates вынести в отдельные файлы |
| Hooks в промптах | Hooks в скриптах — агент не может забыть |
| Нет review workflow | Критические баги попадают в мерж |
| Нет architecture-decisions | Агент предлагает отвергнутые варианты снова |
| Memory растёт бесконечно | Архивировать, держать MEMORY.md < 100 строк |
