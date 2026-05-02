---
name: orm-pulse
description: ORM-конвейер мониторинг для клиентов с reputation management. Собирает Sheet snapshot + TG-экспорт релевантных чатов + Playwright live-парс целевой площадки → reconciliation 3-источников → STATUS-ALL.md. Триггеры — 'orm-pulse', 'orm pulse', 'orm пульс', 'orm статус', 'аудит отзывов', 'orm аудит', 'reputation pulse', 'статус отзывов клиента'. Сейчас работает для BluMart (reviews.yandex.ru). Расширяется на других ORM-клиентов через registry.yaml.
---

# ORM Pulse — мониторинг ORM-конвейера

## Назначение

Один скилл — три вопроса:
1. **Что заказано** (через Sheet + TG)
2. **Что опубликовано** (через live-парс целевой площадки)
3. **Что делать дальше** (через diff vs предыдущий прогон + биржевые пинги)

## Использование

```
/orm-pulse blumart            # один прогон
/orm-pulse blumart --report   # публичная версия (без исполнителей/цен) для клиента
/orm-pulse blumart --watch    # cron 09:00 daily
```

## Pipeline (12 этапов)

| # | Этап | Скрипт | Длительность |
|---|------|--------|:------------:|
| 1 | Загрузка registry.yaml клиента | `scripts/load-registry.py` | 1 сек |
| 2 | Sheet snapshot (все вкладки через curl + Safari cookies) | `scripts/sheet-snapshot.sh` | 5-10 сек |
| 3 | Telethon export 4-6 чатов клиента (клон-сессия) | `scripts/tg-export-clone.py` | 30-60 сек |
| 4 | Playwright live-парс площадки | `scripts/playwright-reviews.py` | 3-5 мин |
| 5 | Match Sheet ↔ Live по тексту/автору | `scripts/match-sheet-live.py` | 10 сек |
| 6 | Reconciliation 3-источник (TG vs Sheet vs Live) | `scripts/reconcile.py` | 5 сек |
| 7 | Pending-buckets автоматически | в `reconcile.py` | — |
| 8 | TG-сигналы пинга (биржа просит ещё) | `scripts/tg-signals.py` | 10 сек |
| 9 | Compose STATUS-ALL.md (Jinja2 template) | `scripts/compose-status.py` | 5 сек |
| 10 | Diff vs предыдущий запуск | в `compose-status.py` | — |
| 11 | Alert-роутер (TG/Asana при critical) | `scripts/alert-router.py` | 5 сек |
| 12 | Git auto-commit | `scripts/commit.sh` | 5 сек |

**Итого ~5-7 минут на прогон.**

## Структура

```
~/.claude/skills/orm-pulse/
├── SKILL.md              # этот файл
├── scripts/
│   ├── load-registry.py
│   ├── sheet-snapshot.sh
│   ├── tg-export-clone.py
│   ├── playwright-reviews.py
│   ├── match-sheet-live.py
│   ├── reconcile.py
│   ├── tg-signals.py
│   ├── compose-status.py
│   ├── alert-router.py
│   └── commit.sh
└── templates/
    └── STATUS-ALL.md.j2  # Jinja2 шаблон
```

Per-client конфиг живёт в репо клиента:
```
~/artvision-data/clients/<client>/orm/registry.yaml
~/artvision-data/clients/<client>/orm/STATUS-ALL-{date}.md  # output
~/artvision-data/clients/<client>/orm/snapshots/             # CSV history
```

## Источники данных

| Источник | Формат | Свежесть |
|----------|--------|----------|
| Google Sheets | curl + Safari cookies → CSV | live (зависит от cookies) |
| TG-чаты | Telethon-клон-сессия (`/tmp/tl-<client>.session`) | live |
| Целевая площадка | Playwright (Chromium, persistent context) | live |
| Snapshot history | git-commit'ы snapshots/ | архив для diff |

## Что НЕ автоматизируется

- Согласование текстов модератором клиента (Юра у BluMart) — TG, не API
- Генерация ФИО заказчиков (Иришка у BluMart) — внутренний CRM клиента
- Восстановление kwork-логина и подобное — 2FA / recovery
- Финансовые потоки между Артвишн ↔ клиент — out of scope
- Передача партий исполнителю — Андрей К. вручную (TG + Sheet)

## Безопасность

- **Read-only** по всем источникам.
- НЕ редактирует Sheet.
- НЕ отправляет TG-сообщения никому.
- ORM-секрет (контрагенты, цены, биржи) — только во INTERNAL версии STATUS-ALL. Для `--report` версии исключается.

## Запуск без скилла (manual fallback)

Если скилл не вызывается (например, в фоне) — можно запустить руками:
```bash
SLUG=blumart
~/.claude/skills/orm-pulse/scripts/sheet-snapshot.sh $SLUG
~/.claude/skills/orm-pulse/scripts/tg-export-clone.py $SLUG
~/.claude/skills/orm-pulse/scripts/playwright-reviews.py $SLUG
~/.claude/skills/orm-pulse/scripts/match-sheet-live.py $SLUG
~/.claude/skills/orm-pulse/scripts/reconcile.py $SLUG
~/.claude/skills/orm-pulse/scripts/compose-status.py $SLUG
```

## Реестр клиентов с ORM

Добавлять новых клиентов: создать `clients/<client>/orm/registry.yaml` по шаблону `templates/registry.yaml.example`.

Активные клиенты:
- **blumart** (с 2026-04, основной)

Потенциальные:
- (никто не запущен на ORM кроме BluMart на 2026-05-01)
