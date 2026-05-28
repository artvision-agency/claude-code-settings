# Agent #2 — Aggregators (2GIS + Zoon + локальный каталог)

**Subagent type:** `general-purpose` (нужен Bash + WebFetch + WebSearch)

## Задача

Собрать данные с агрегаторов-альтернатив Я.Карт для каждой организации из `<base>/data/seed-orgs.json`:
- 2GIS — рейтинг, отзывы, темы
- Zoon — рейтинг, отзывы, темы (где нет блокировок)
- Локальный каталог под нишу:
  - Школы СПб: `apeterburg.com`, `shkola.city`, `schoolotzyv.ru`
  - Клиники: `prodoctorov.ru`, `napopravku.ru`, `docdoc.ru`
  - Детсады СПб: `apeterburg.com` (раздел детсадов), `littleone.ru`
  - Стоматологии: `prodoctorov.ru` + `stomatologija.su`
  - Универсал: `flamp.ru`, `otzovik.com`

## Метод

1. Прочитать `<base>/data/seed-orgs.json`
2. Для каждой организации:
   - `WebSearch`: `<название> <город> 2GIS` → найти URL → `WebFetch`
   - То же для Zoon и локального каталога
   - Записать rating, reviews_count, top-3 темы +/-
3. Важно — **профиль каждого агрегатора:**
   - **2GIS** — рейтинг занижен (более строгая аудитория, бытовая критика)
   - **Zoon** — рейтинг часто полярный (либо 5, либо 1-2)
   - **Локальный каталог** — самые подробные отзывы, но малая выборка
4. Не дублировать темы из Я.Карт — фокус на специфике агрегатора (бытовая критика, поборы, отдельные сотрудники).

## Выход

Записать в `<base>/data/orgs-aggregators.json`:

```json
{
  "collected": "YYYY-MM-DD",
  "agent": "aggregators",
  "sources": ["2gis.ru", "zoon.ru", "<local>"],
  "orgs": [
    {
      "id": "<seed-id>",
      "name": "<имя>",
      "2gis": {
        "url": "<url или null>",
        "rating": 4.1,
        "reviews_count": 23,
        "themes_positive": [...],
        "themes_negative": [...]
      },
      "zoon": {
        "url": "...",
        "rating": 2.8,
        "reviews_count": 12,
        "polarization_note": "<если есть>",
        "themes_positive": [...],
        "themes_negative": [...]
      },
      "local_catalog": {
        "source": "apeterburg.com | prodoctorov.ru | ...",
        "url": "...",
        "rating": null,
        "reviews_count": 51,
        "themes_positive": [...],
        "themes_negative": [...]
      }
    }
  ]
}
```

## Антипаттерны

- ❌ Записать «не нашёл» если 2gis заблокирован → попробовать через WebSearch snippet
- ❌ Сравнивать рейтинг 2GIS и Я.Карт напрямую (разные шкалы) → отметить расхождение, не делать вывод
- ❌ Игнорировать локальный каталог если есть городской лидер (СПб → apeterburg) — там самые подробные отзывы
