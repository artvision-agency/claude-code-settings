# Канонический прайс клиник — clinics-pricing.json ОБЯЗАТЕЛЕН (источник правды, мульти-источник+сверка) — DEFAULT ON, HARD

> **Установлено:** 2026-06-27 (Антон, USmile анализ цен соседей). «У нас должен быть общий ценовой прайс по каждой клинике, который сходится с сайтом, с ПроДокторов и т.д. Чтобы это всегда было записано, файл всегда присутствовал.» Спроектировано Claude Code × Codex.
> **Спека:** `artvision-data/docs/processes/clinic-pricing-canonical-structure.md`. **Схема:** `artvision-data/docs/schemas/clinic-pricing.schema.json`.
> **Связано:** `parsing-read-pdfs.md`, `numbers-deterministic-meaning-llm.md`, `source-consolidation-verify.md`, `calculations-need-sources.md`, `template-selection-map.md` (класс visibility/dashboard), `competitor-pricing-calculator-scenario.md`.

## Правило (HARD)
Для ЛЮБОГО проекта с анализом цен конкурентов/соседних клиник/локального рынка — цены живут в КАНОНИЧЕСКОМ файле, НЕ зашиты в HTML:
- **`clients/<slug>/presale/clinics-pricing.json`** — единственный источник правды цен. Создаётся при онбординге (болванка с null), не удаляется, всегда присутствует.
- Валидируется по `docs/schemas/clinic-pricing.schema.json`.
- HTML-матрица — ПРОИЗВОДНЫЙ артефакт: данные инлайнятся в неё СКРИПТОМ сборки из JSON (правило автономности HTML — без fetch), цифры в HTML не правят руками.

## Структура (суть)
`meta` (slug, бренд, ниша, город, calc_center-координаты напр. метро, radius_m, conflict_threshold_pct=20, stale_after_days=90) → `service_taxonomy[]` → `clinics[]` (name, address, lat/lon, distM, segment, is_target, sources-статусы) → услуга → **`readings[]`** (каждое чтение: value, kind exact/from/range/promo, source_name, source_url, checked_at MSK, confirmed, parser{method,rule_id,selector,evidence,snapshot}) + вычисленный **`canonical`** + **`reconciliation_status`**.

## Мульти-источник + сверка (главное)
- Каждая цена сверяется по нескольким источникам: **свой сайт > ПроДокторов > агрегаторы** (2gis/zoon/32top/stom-firms) > manual_override.
- `reconciliation_status`: empty / single_source / **agreed** (2+ совпали ≤порога) / **conflict** (расхождение >20% → хранить все значения + флаг) / stale / manual_override.
- Не найдено → `null` (НЕ 0; 0 только если источник явно «бесплатно»). checked_at старше 90 дн → `stale`.

## Детерминизм
Цены тянутся КОДОМ (css/xpath/table/json_ld/regex/pdf/api — `parsing-read-pdfs`), не «на глаз». Каждая = source_url + дата + evidence (+snapshot). Перенос/расчёт — кодом, не выводом LLM (`numbers-deterministic`).

## Антипаттерны
- ❌ Цены зашиты в HTML как первоисточник (хрупко, теряется, не сверяется).
- ❌ Цена без source_url/checked_at.
- ❌ `0` вместо `null` для «не найдено».
- ❌ Правка цифр в HTML руками вместо JSON → сборка.
- ❌ Проект с конкурентным анализом без `clinics-pricing.json`.

## Применение / TODO
- Готово: USmile (`clients/usmile/presale/clinics-pricing.json`, 8 клиник, 11 услуг, схема VALID).
- Перенести: Творим (`tvorim-sovershenstvo`) — отдельно.
- Кандидат-скилл `/clinic-pricing <slug> [--refresh|--validate|--build-matrix]` (болванка при онбординге, сбор readings, пересчёт canonical, валидация, сборка HTML). Реализовать отдельной сессией.

## Sync
`~/.claude/rules/` → 3 аккаунта. Схема/спека — в artvision-data/git.
