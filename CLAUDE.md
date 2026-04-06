# Claude Instructions

## Старт сессии

1. git pull → PROJECTS.md → TODO.md текущего контекста
2. Показать открытые задачи → TaskCreate для каждой
3. После compaction/resume → парсить summary → TaskCreate для pending items

## Rules (~100 строк, загружаются всегда)

| Файл | Что |
|------|-----|
| `core.md` | Автономность, skills, данные, VPS, массовые операции |
| `context.md` | TODO routing, старт сессии, compaction recovery |
| `security.md` | AUTO/CONFIRM, табу AI в публичных, токены |
| `git.md` | Auto-commit, проекты, аккаунты |
| `self-check.md` | Топ-5 повторяющихся ошибок |
| `shortcuts.md` | Ключевые команды (полный словарь → skill `shorthand`) |

## Skills (загружаются по запросу)

Полный словарь опечаток → `shorthand`. Детали workflow → `artvision-workflow`. Маршрутизация агентов → `agent-roster` (skill `run-agent`). Quality gates → `quality-gates` (skill `factcheck`).
