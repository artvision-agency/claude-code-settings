# Сессия и TODO

## Старт сессии

1. `git pull` → прочитать `artvision-data/PROJECTS.md` (source of truth)
2. Прочитать TODO.md текущего контекста → показать открытые задачи
3. TaskCreate для КАЖДОЙ pending задачи — СРАЗУ, без напоминания
4. Показать меню перекрёстка (ниже)

## TODO-маршрутизация

| cwd / контекст | TODO файл |
|----------------|-----------|
| `~/artvision-data` (ops) | `artvision-data/TODO.md` |
| `~/artvision-tg-bot` (bot) | `artvision-tg-bot/TODO.md` |
| `~/devops-agent` (infra) | `devops-agent/TODO.md` |
| presale | `artvision-data/presale/TODO.md` |
| products | `artvision-data/products/TODO.md` |

Новая задача → в нужный TODO по контексту. Конец сессии → commit + push TODO*.md.

## Меню перекрёстка

| Ввод | Действие |
|------|----------|
| `1`/`го`/`комбайн` | TODO → подтверждение → `/combine` |
| `2`/`интервью`/текст задачи | Уточнить (для кого, результат, срочность) → разбить → очередь |
| `3`/`туду`/`обзор` | Показать все задачи |
| `4`/`синк`/`sync` | `/sync-sessions` |
| `5`/`фикс`/мелочь | Сделать сразу, без очереди |

## Формат задачи в TODO

```
- [ ] Описание [client:X] [result:X] [priority:high] [skill:auto]
```

Задача ready = все 4 обязательных поля заполнены. НЕ ready → мини-интервью (1-2 вопроса).

## После compaction/resume

Парсить summary → TaskCreate для КАЖДОГО pending item. Обещание в тексте = TaskCreate сразу.

## Sync между аккаунтами

TODO в git → `git pull` подтягивает. Начало: pull. Конец: commit + push.

## Ops = CRM: единый реестр задач

`artvision-data/` — **CRM Artvision**. Все задачи отовсюду (Bot Dev, DevOps, Home, Asana, TG, email, meetings) должны быть видны здесь.

- `PROJECTS.md` = source of truth проектов и клиентов
- `TODO.md` + `presale/TODO.md` + `products/TODO.md` = реестр задач
- Задача в не-Ops сессии → дублируется в `artvision-data/TODO.md` с тегом `[session:bot-dev|devops|home]`
- Asana ↔ TODO ↔ `/combine` — двусторонняя связка: создание + статусы синкаются
- `/combine` читает 5 TODO + Asana, фильтрует по `[session:]`, запускает из нужного cwd
- Раз в день (09:00 брифинг) — мердж 5 TODO, закрытие дублей
