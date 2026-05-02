---
name: orm-pulse
description: ORM-конвейер командный центр для клиентов с reputation management. Агрегирует Sheet + TG (Telethon) + qcomment API + reviews.yandex.ru live + executor-ledger + research → единый HTML-дашборд + TG-алёрты команде. Авто-refresh 30 мин. Триггеры — 'orm-pulse', 'orm pulse', 'orm пульс', 'orm статус', 'командный центр', 'orm дашборд', 'orm аудит', 'reputation pulse'. Сейчас работает для BluMart (reviews.yandex.ru). Расширяется через registry.yaml.
---

# ORM Pulse — командный центр ORM-workflow

## Назначение

Единый pipeline и live-дашборд для всех источников ORM-данных клиента:
1. **Что заказано** — Sheet1/Sheet2 (snapshot + diff)
2. **Что опубликовано** — reviews.yandex.ru live (rating/total/темп через LaunchAgent 4×/день)
3. **Что в работе** — qcomment API (balance/проекты/pending), TG биржи, kwork (manual session)
4. **Кому отдано** — executor-ledger (append-only CSV журнал передач)
5. **Что делать дальше** — alert-router в TG команды (НЕ заказчикам!) + research отчёты
6. **Где искать** — tg-discover-serm + контакты подрядчиков в registry.yaml

## Live URLs (X-Robots-Tag noindex)

- 🎯 **Command Center**: https://artvision.pro/orm-command-center/<slug>.html
- 📊 QComment dashboard: https://artvision.pro/qcomment/
- 🤝 Contractors HTML: https://artvision.pro/orm-contractors.html
- 🔬 Research: https://artvision.pro/orm-research/<slug>-*.html

## Использование

```bash
# Главный режим — full pipeline + deploy command-center + alerts
~/.claude/skills/orm-pulse/scripts/auto-refresh.sh <client>

# Отдельные режимы
./scripts/run.sh <client> qcomment        # только qcomment snapshot
./scripts/run.sh <client> orders-state    # Sheet воронка + qcomment блок
./scripts/run.sh <client> ledger          # executor-ledger stats
./scripts/run.sh <client> full            # все источники, без deploy

# Discovery
./scripts/tg-discover-serm.py <client> --global-search --scan-subs

# Командный центр
./scripts/command-center.py <client> --deploy

# Research отчёты деплой
./scripts/deploy-research.py <client> <md_filename>
./scripts/deploy-research.py --all <client>

# Алёрты в TG команды (rate-limit 6h)
./scripts/alert-router.py <client> [--dry-run] [--force]

# Executor ledger
./scripts/executor-ledger.py add <client> --executor X --channel Y --status sent --text "..."
./scripts/executor-ledger.py backfill <client> --source qcomment
./scripts/executor-ledger.py stats <client>
```

## Setup для нового клиента / восстановления сессий

См. `SETUP.md` рядом — пошаговая инструкция для:
- Telethon (TG export, alerts, discover) — общая сессия
- Google Sheets — Safari cookies
- QComment — API key (уже в tokens.json)
- Kupi-otziv — Cookie-Editor → Netscape txt
- Kwork — manual Chrome session ИЛИ kwork API
- Zenno.club — auth не требуется

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
