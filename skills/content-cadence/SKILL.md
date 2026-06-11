---
name: content-cadence
description: "Ramp-up расписание публикации статей чтобы Google не пометил как spam при онбординге клиента с большим архивом контента. Алгоритм: день N → ceil(N/3) постов. Triggers: 'content cadence', 'расписание публикаций', 'ramp-up контент', 'drip publish', 'cadence', 'график публикации', 'не палить google', 'анти-spam расписание', 'content velocity'."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Content Cadence — Ramp-up расписание публикаций

## Назначение

Клиент приходит с архивом 30-100+ готовых статей (Творим, presale-онбординг). Залить всё сразу = unnatural growth pattern → Google пометит как spam → demotion в SERP.

Скилл строит **ramp-up расписание**: первые дни мало постов, нарастание плавное. Имитирует естественный рост публикаций нового активного блога.

## Алгоритм ramp-up

```
day(n) = min(target_daily_max, ceil(n/3))
```

| День | Постов | Кумулятив |
|------|--------|-----------|
| 1    | 1      | 1         |
| 2    | 1      | 2         |
| 3    | 1      | 3         |
| 4    | 2      | 5         |
| 5    | 2      | 7         |
| 6    | 2      | 9         |
| 7    | 3      | 12        |
| 10   | 4      | 22        |
| 14   | 5      | 36        |
| 21   | 5 (cap) | ~60      |

Параметры по умолчанию: `target_daily_max=5`, `weekdays_only=true` (B2B), `hour_window=09:00-11:00 МСК`, `jitter=±30 min`.

## Когда использовать

| Триггер | Действие |
|---------|----------|
| Клиент даёт N готовых статей при онбординге | `/content-cadence build --count N` |
| Расширение существующего блога после паузы | `--mode resume` (старт с day=5 если блог уже активен) |
| Антипаттерн: «залей все 50 статей завтра» | СТОП → объяснить риск → построить cadence |

## Workflow

1. **Сбор входа** — N статей (URL/paths/draft IDs), CMS клиента (WP/MODX/Bitrix), дата старта, target_daily_max
2. **Build schedule** — `scripts/build_schedule.py` → JSON-расписание (article → date+time)
3. **Review** — показать таблицу Антону / клиенту, утвердить
4. **Auto-publish** — переиспользовать существующий скилл `page-publish` (WP REST / MODX Playwright / Bitrix webform), НЕ дублировать публикацию
5. **GSC submit** — после публикации каждой статьи `seo-google` → Search Console URL inspection / submit
6. **Verify** — `verify_indexed.py` через 24ч/7д проверяет индекс. Не индексировалось 7 дней → переоткрытие в очередь (+jitter)
7. **Лог** — всё в `clients/<slug>/content-cadence/log.jsonl`

## Constraints

- **B2B клиенты:** `weekdays_only=true` (Пн-Пт), `hour_window=09:00-11:00 МСК` — пиковый Google crawl + рабочее время
- **B2C клиенты:** можно вкл. выходные, окно шире (10:00-14:00 + 18:00-21:00)
- **Jitter ±30 мин** — рандомизация времени, чтобы не выглядеть как cron-bot
- **Праздники РФ** — пропускать (статьи переносятся на следующий рабочий день)
- **Holidays файл:** `~/.claude/data/ru-holidays-2026.json` (если есть, иначе по календарю Pn-Пт)

## Использование

```bash
# 1. Построить расписание
python3 ~/.claude/skills/content-cadence/scripts/build_schedule.py \
  --count 50 \
  --start 2026-05-26 \
  --target-daily-max 5 \
  --weekdays-only \
  --output clients/<slug>/content-cadence/schedule.json

# 2. Опционально передать список URL/paths:
python3 ... --articles articles.txt --output schedule.json

# 3. Опубликовать (через page-publish skill — НЕ из этого скилла напрямую)
# Skill page-publish читает schedule.json и публикует по дням

# 4. Verify через неделю
python3 ~/.claude/skills/content-cadence/scripts/verify_indexed.py \
  --schedule clients/<slug>/content-cadence/schedule.json \
  --gsc-property https://example.com/
```

## Структура schedule.json

```json
{
  "client": "tvorim",
  "start_date": "2026-05-26",
  "target_daily_max": 5,
  "weekdays_only": true,
  "hour_window": ["09:00", "11:00"],
  "total_articles": 50,
  "total_days": 18,
  "items": [
    {"day": 1, "date": "2026-05-26", "time": "09:23", "article_idx": 0, "article": "url-or-path", "status": "scheduled"},
    {"day": 1, "date": "2026-05-26", "time": null, "article_idx": null, "status": "skipped"}
  ]
}
```

## Интеграция с другими скиллами

- **`page-publish`** — реальная публикация (WP REST API / MODX Playwright / Bitrix webform). НЕ дублировать.
- **`seo-google`** — GSC URL inspection + submit после публикации.
- **`content-writer`** — если статьи ещё не написаны, передать список тем для генерации перед cadence.
- **`programmatic-seo`** — если статьи генерятся пачкой по шаблону, всё равно через cadence.

## Стандарты Артвижн

- `~/.claude/rules/proven-tools-first.md` — перед написанием wp-publisher проверить готовые (WP-CLI `wp post create --post_status=future`, GitHub `wordpress-scheduler` пакеты). См. также проверенный WP-CLI flag `--post_date='YYYY-MM-DD HH:MM:SS' --post_status=future` — нативный механизм отложенной публикации.
- `~/.claude/rules/no-smoothing.md` — если jitter поднял время вне `hour_window`, явно лог-WARN, не «сгладить».
- `~/.claude/rules/quality.md` — verification перед «готово»: schedule.json валиден (всем item.date/time выставлен ИЛИ status=skipped).

## Антипаттерны

- ❌ Залить 50 статей за 1 день «потому что клиент хочет быстрее» → spam-сигнал Google
- ❌ Публиковать всё точно в 09:00:00 → bot-pattern → ручной penalty риск
- ❌ Дублировать публикационный код WP/MODX в этом скилле → переиспользовать `page-publish`
- ❌ Игнорировать праздники РФ → у статей даты на 8 марта / 9 мая выглядят странно

## Прецеденты применения

- **Творим (2026-05):** 80+ готовых статей с старого блога. Без cadence риск demotion. План — 22 дня ramp-up (1→1→1→2→2→2→3...5/день).
- **Новые presale-клиенты** с архивом — стандартно перед запуском SEO кампании.

## История эволюции

- **2026-05-21** — создан. Базовый ramp-up calculator + интеграция с `page-publish` / `seo-google`.
- TBD: publish_wp.py / publish_modx.py / verify_indexed.py — реализация (сейчас заглушки).
- TBD: holidays-РФ автоматически из `~/.claude/data/ru-holidays-{year}.json`.
