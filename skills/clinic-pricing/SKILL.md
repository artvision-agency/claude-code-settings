---
name: clinic-pricing
description: Канонические цены соседних клиник/конкурентов по стандарту Artvision (clinic-pricing-canonical-structure.md). Валидация JSON по схеме, детерминированный парс ЦЕН С САЙТА клиники (regex/CSS/таблицы/JSON-LD/PDF, числа НЕ через LLM), пересборка HTML-матрицы цен из canonical JSON. Триггеры — 'собери прайс клиники', 'clinic pricing', 'прайс конкурентов', 'обнови цены клиники', 'матрица цен клиник', 'цены соседних клиник', 'competitor pricing matrix', 'спарси цены с сайта клиники'. Источник правды = clients/<slug>/presale/clinics-pricing.json, HTML — производный артефакт.
---

# Clinic Pricing — канонические цены клиник

Детерминированный CLI поверх стандарта `docs/processes/clinic-pricing-canonical-structure.md` и схемы `docs/schemas/clinic-pricing.schema.json`.

Принцип: **цены — единый JSON-источник правды**, HTML-матрица собирается из него. Числа извлекаются regex/селектором/таблицей, **не LLM** (numbers-deterministic-meaning-llm). Цены не выдумываются: `parse-site` пишет только то, что реально нашёл на странице; не найдено → `null`/`no_price`.

## CLI

Скрипт: `scripts/clinic_pricing.py` (запускать из `artvision-data/`).

| Команда | Что делает |
|---|---|
| `python3 scripts/clinic_pricing.py validate <slug>` | Валидирует `clients/<slug>/presale/clinics-pricing.json` по JSON Schema. Выводит VALID/INVALID + completeness (сколько услуг с `canonical.value != null` на клинику). |
| `python3 scripts/clinic_pricing.py build <slug>` | Пересобирает HTML-матрицу `clients/<slug>/presale/*competitor-matrix*.html` из JSON. Жёсткий гейт радиуса (>`radius_m`, по умолч. 2 км) — дальние клиники в матрицу не попадают (целевая — всегда). Для usmile вызывает существующий `build-matrix-data.py`. |
| `python3 scripts/clinic_pricing.py parse-site <slug> --clinic <id> --url <url> [--date YYYY-MM-DD]` | Детерминированный парс цен **с официального сайта клиники** (httpx/requests + BeautifulSoup; PDF → pdfplumber). Матчит услуги по `service_taxonomy[].synonyms`, пишет reading {value,kind,source_name:"site",source_url,checked_at,confirmed,parser{method,evidence}}, пересчитывает `canonical` + `reconciliation_status` + `conflict`. Идемпотентно (заменяет прежнее site-чтение этого URL). Валидирует результат по схеме перед записью. |
| `python3 scripts/clinic_pricing.py add-aggregator-stub` | Показывает TODO: адаптеры агрегаторов (prodoctorov/2gis/zoon/32top/stom-firms) **НЕ реализованы** (заглушка, отдельная сессия — антибот/капча). |

## Типовой ход

1. `validate <slug>` — убедиться что canonical-файл валиден.
2. По реальному URL прайса клиники: `parse-site <slug> --clinic <id> --url <...>` — спарсить site-цены.
3. (агрегаторы — пока вручную/заглушка; приоритет источников: site > prodoctorov > 2gis/zoon/32top/stom-firms > manual_override).
4. `validate <slug>` снова → `build <slug>` → проверить HTML (mobile, дальние клиники исключены) → deploy при необходимости.

## Важно
- Цены вручную в HTML НЕ менять — только в `clinics-pricing.json`, затем `build`.
- `parse-site` работает только на реальном URL по запросу; цены не выдумываются.
- Агрегаторы — заглушка-TODO (`parse_aggregator` → `NotImplementedError`).
- Каждый новый клиент с анализом цен конкурентов обязан иметь `clients/<slug>/presale/clinics-pricing.json` (стандарт «файл всегда есть»).

## Связано
- Стандарт: `docs/processes/clinic-pricing-canonical-structure.md`
- Схема: `docs/schemas/clinic-pricing.schema.json`
- Пример: `clients/usmile/presale/clinics-pricing.json` (+ `usmile-competitor-matrix.html`)
- Правила: numbers-deterministic-meaning-llm, calculations-need-sources, medical-facts-verification, scraping.md
