# Agent #1 — Yandex Maps

**Subagent type:** `general-purpose` (нужен Bash + WebFetch + WebSearch)

## Задача

Собрать с Я.Карт для каждой организации из `<base>/data/seed-orgs.json`:
- URL карточки на Я.Картах
- Рейтинг (если есть)
- Кол-во отзывов
- Период отзывов (year_from — year_to)
- Темы хвалят (themes_positive) — топ-3..5 с временным разрезом
- Темы ругают (themes_negative) — топ-3..5 с временным разрезом
- Геоверификация — что место реально в target-городе (НЕ другой регион)

## Метод

1. Прочитать `<base>/data/seed-orgs.json` — взять все организации
2. Для каждой:
   - `WebSearch`: `<название> <город> Яндекс Карты` → найти URL карточки `yandex.com/maps/org/...` или `yandex.ru/maps/org/...`
   - `WebFetch <URL>` → собрать rating, reviews_count, sample отзывов
   - **Геоверификация:** проверить что в title/breadcrumbs/адресе фигурирует target-город (НЕ Ижевск, Казань если ищем СПб; и т.п.)
3. Если SmartCaptcha блокирует → пометить `yandex_status: "captcha_blocked"`, заполнить через fallback:
   - `apeterburg.com` (СПб) или `2gis.ru` или `zoon.ru` snippets через WebSearch
   - Помечать `source_fallback: "<имя>"`
4. NLP-темы:
   - Группировать отзывы по 2 эрам: «2018-2023» и «2024-2026»
   - Для каждой темы `delta`: «+» / «-» / «новое» / «стабильно»
   - Считать долю упоминаний (топ-5)

## Выход

Записать в `<base>/data/orgs-yandex.json`:

```json
{
  "collected": "YYYY-MM-DD",
  "agent": "yandex-maps",
  "method": "...",
  "captcha_rate": "X%",
  "data_quality_note": "...",
  "orgs": [
    {
      "id": "<seed-id>",
      "name": "<имя>",
      "yandex_url": "<url или null>",
      "yandex_status": "direct_fetch_ok | captcha_blocked | not_found",
      "city_verified": true | false,
      "city_actual": "<если city_verified=false>",
      "rating": 4.2,
      "reviews_count": 70,
      "reviews_period": "2018-2025",
      "themes_positive": [
        {"theme": "<краткая формулировка>", "delta": "+/-/новое/стабильно", "note": "<опц>", "year": "<опц>"}
      ],
      "themes_negative": [
        {"theme": "...", "delta": "+", "year": "2024-2025"}
      ],
      "source_fallback": "<если captcha>"
    }
  ]
}
```

## Антипаттерны

- ❌ Записать `yandex_url` без проверки города → подмена места (СОШ 91 → Ижевск)
- ❌ Использовать только сводный рейтинг без тем → потеря сигнала
- ❌ Складывать все эры отзывов в кучу → теряется тренд деградации/улучшения
- ❌ Записать «отзывов 0» если просто не смог достучаться → честно `captcha_blocked`

## Связь

- Hook `pre-yandex-maps-place-check.sh` блокирует подмены при Write
- Если 80%+ captcha — записать в `data_quality_note` и продолжить через fallback
