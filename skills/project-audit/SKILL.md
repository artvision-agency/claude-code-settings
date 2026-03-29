---
name: project-audit
description: Use when setting up Claude Code infrastructure for a project — audits and creates missing rules, templates, hooks, architecture decisions, and archives stale memory. Use when starting a new project, onboarding to existing one, or when user says "audit", "set up .claude", "create hooks", "project structure"
---

# Project Audit

Аудит и настройка инфраструктуры Claude Code по best practices (Habr: "Как не дать проекту деградировать").

## Overview

Анализирует `.claude/` структуру проекта и создаёт недостающее: rules, templates, hooks, architecture decisions. Упрощает CLAUDE.md если раздут.

## When to Use

- Новый проект без `.claude/` инфраструктуры
- Существующий проект — хочется навести порядок
- После прочтения статьи про деградацию проекта
- Пользователь говорит "аудит", "настрой .claude", "создай хуки"

## Audit Checklist

Выполняй **строго по порядку**. Каждый шаг — отдельная задача в TaskCreate.

### Step 1: Анализ текущего состояния

Проверить наличие и содержимое:

```
.claude/
  rules/          — есть? сколько файлов? покрывают ли стиль, профиль, архитектуру?
  templates/      — есть? шаблоны под стек проекта?
  scripts/        — есть? hooks подключены в settings?
  skills/         — есть? проектные skills?
  agents/         — есть? субагентные инструкции?
CLAUDE.md         — сколько строк? (>200 = раздут)
memory/           — сколько файлов? есть ли устаревшие?
settings.local.json — hooks подключены?
```

Вывести таблицу: что есть ✅, чего нет ❌, что требует улучшения ⚠️.

### Step 2: Hooks (максимальный эффект)

Создать `.claude/scripts/` с тремя хуками:

**hook-post-commit.sh** — напоминание после `git commit`:
- Обновить memory/docs
- Нужен ли deploy
- Нужен ли git push

**hook-pre-deploy.sh** — блокировка деплоя:
- Проверка непушнутых коммитов (exit 2 если есть)
- Warning о незакоммиченных изменениях
- Адаптировать команду деплоя под проект (deploy.sh, docker compose, etc.)

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

### Step 3: Rules

Создать `.claude/rules/` — вынести из CLAUDE.md пассивный контекст:

**coding-style.md** (globs: `["**/*.{py,ts,js,go}"]`):
- Логирование (формат, библиотека)
- DB-паттерны (ORM, сессии, миграции)
- Форматирование, линтинг
- Специфичные gotchas проекта

**profile.md** (globs: `["**/*"]`):
- Язык общения
- Уровень автономности
- Что НЕ делать без спроса
- Предпочтения по инструментам

**architecture.md** (globs: `["**/*.{py,ts,js,go}"]`):
- Ключевые архитектурные паттерны
- Pipeline/очереди
- Ссылки на templates

Каждый rule-файл с frontmatter:
```yaml
---
description: краткое описание
globs: ["**/*.py"]
---
```

### Step 4: Templates

Создать `.claude/templates/` — шаблоны для типовых операций проекта.

Определить шаблоны по стеку:
- **Python web**: новый эндпоинт, миграция, модель, тест
- **React/TS**: новый компонент, страница, хук
- **Bot (aiogram)**: новый хендлер, FSM, клавиатура
- **Scraper**: новый парсер сайта, новый источник
- **General**: новый канал/ресурс

Каждый шаблон содержит:
1. Скелет файла с TODO-комментариями
2. Чеклист (что не забыть)
3. Где зарегистрировать новый код

### Step 5: Architecture Decisions

Создать `memory/architecture-decisions.md` если нет.

Формат ADR:
```markdown
## ADR-NNN: Название
**Решение**: что выбрали
**Причина**: почему
**Отвергнуто**: что рассматривали и почему отказались
**Дата**: YYYY-MM-DD
```

Собрать из: git history, CLAUDE.md, memory-файлов, разговора с пользователем.

### Step 6: Упрощение CLAUDE.md

Если CLAUDE.md > 100 строк:
- Вынести Code Style → `rules/coding-style.md`
- Вынести Key Patterns → `rules/architecture.md`
- Вынести User Preferences → `rules/profile.md`
- Оставить: Project, Quick Commands, Tech Stack, Architecture (дерево), DB Models, Admin Commands
- Добавить секцию "Rules & Templates" со ссылками

Целевой размер: **60-90 строк**.

### Step 7: Архивирование memory

Если есть memory-файлы:
- Проверить каждый на актуальность
- Устаревшие (завершённые миграции, старые планы) → `memory/archive/`
- Обновить MEMORY.md — убрать мёртвые ссылки, добавить новые
- Целевой размер MEMORY.md: **< 100 строк** (после 200 — обрезается)

## Common Mistakes

| Ошибка | Исправление |
|--------|-------------|
| Всё в CLAUDE.md | Rules/templates вынести в отдельные файлы |
| Hooks в промптах | Hooks в скриптах — агент не может забыть |
| Нет architecture-decisions | Агент будет предлагать отвергнутые варианты снова |
| Memory растёт бесконечно | Архивировать завершённое, держать MEMORY.md < 100 строк |
| Templates без чеклиста | Агент забудет зарегистрировать код |
