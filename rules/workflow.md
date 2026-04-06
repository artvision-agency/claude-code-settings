# Стиль работы

## Superpowers + Git = ДЕФОЛТ

Разработка: Brainstorming → Plan → TDD → Implementation → Code Review → Verification → Commit → Deploy.
ЗАПРЕЩЕНО: править код на VPS/продакшене. Только: git repo → commit → push → deploy script.

## Обязательные скиллы

| Задача | Скилл |
|--------|-------|
| КП клиенту | `presale-kp` |
| SEO | `seo-master` |
| Контент | `content-writer` |
| Бот-деплой | `telegram-bot-deployment` |
| Код-ревью | `code-audit` |
| CRO | `cro` |
| Schema | `schema-markup` |
| Линкбилдинг | `linkbuilding` |
| Реклама | `paid-ads` |

Скилл = ПЕРВЫЙ шаг. Не после, не "если время будет".

## Фоновый мониторинг

Длинный процесс (>2 мин) → `/loop` + работай дальше. Деплой → `/loop 2m`.

## Claude Cron (при старте)

- 09:00: брифинг (git pull, Asana overdue, план → TG)
- 13:00: midday check
- 18:00: sync (итоги, memory, git push)

## Shell-скрипты

`set -euo pipefail`. macOS: `sed -i ''`, `grep -c` может вернуть пустую строку.

## Еженедельный self-review (ВС)

LaunchAgent → weekly-learning.sh → обновить lessons, patterns, MEMORY.md.
