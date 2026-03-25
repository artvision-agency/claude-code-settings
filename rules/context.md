# Контексты и TODO

## TODO по cwd

| cwd | Сессия | TODO |
|-----|--------|------|
| `~/artvision-data` | Artvision Ops | `artvision-data/TODO.md` |
| `~/artvision-tg-bot` | Bot Dev | `artvision-tg-bot/TODO.md` |
| `~/devops-agent` | DevOps | `devops-agent/TODO.md` |

Presale: `artvision-data/presale/TODO.md` | Products: `artvision-data/products/TODO.md`

## Старт сессии

1. git pull → прочитать PROJECTS.md (source of truth) → TODO.md текущего контекста
2. Показать открытые задачи → TaskCreate для каждой pending
3. Показать меню (skill `session-start` для полного меню)

## После compaction/resume

Парсить summary → TaskCreate для КАЖДОГО pending item. Обещание в тексте = TaskCreate сразу.

## Sync

TODO.md живёт в git. Начало: git pull. Конец: commit + push TODO*.md.
