# Модуль сверки присутствия/полноты клиники — clinics-presence.json (сайт vs агрегаторы) — DEFAULT ON

> **Установлено:** 2026-06-27 (Антон, USmile). «Добавить аналитический модуль по сверке цен на сайте и на всех мед-агрегаторах + проверку заполнения: лицензии, врачи, работы — загружено или нет. Если есть на сайте, но нет на агрегаторе — занести. Берём сайты и заносим.» Спроектировано Claude Code × Codex.
> **Спека:** `artvision-data/docs/processes/clinic-presence-audit-module.md`. **Схема:** `artvision-data/docs/schemas/clinic-presence.schema.json` (VALID draft-07).
> **Связано:** `clinic-pricing-canonical.md` (sibling-модуль цен), `medical-facts-verification.md` (лицензии/врачи CONFIRMED+источник), `local-seo`/NAP-аудит (asana.md 6 каталогов), `parsing-read-pdfs.md`, `numbers-deterministic-meaning-llm.md`, `source-consolidation-verify.md`.

## Правило (HARD)
Для проектов клиник/локальных медуслуг — вести **сверку присутствия и полноты** данных клиники по источникам (не только цены):
- **`clients/<slug>/presale/clinics-presence.json`** — канонический файл присутствия, всегда есть (болванка при онбординге), валидируется по `docs/schemas/clinic-presence.schema.json`.
- Отчёт-матрица «элемент × источник» строится ИЗ JSON (не хранит данные в HTML).

## Что проверяется (элементы × источники)
- **Элементы:** prices, **licenses** (№/орган/дата/URL), **doctors** (профили/фото/регалии/сертификаты), **works_cases** (кейсы до/после), reviews (кол-во+рейтинг), services, nap, photos, description.
- **Источники:** site + prodoctorov + 2gis + zoon + 32top + stom-firms + yandex_maps + google_business + napopravku + docdoc.
- **Статус** per элемент per источник: `present` (заполнено) / `empty` (профиль есть, пусто) / `absent` (нет профиля) / `not_checked` / `not_applicable`.

## Gap-анализ (главная ценность)
- есть на site, `absent/empty` на агрегаторе → **`push_to_aggregator`** («взять с сайта → занести на агрегатор X»).
- нет нигде → **`create`** (создать/загрузить).
- есть на агрегаторе, нет на site → **`add_to_site`**.
- **completeness score** per источник и per клиника (% заполненных элементов).

## Медфакты и детерминизм
- Лицензии/врачи — CONFIRMED + источник (`medical-facts-verification`, не из головы; лицензия = №+орган+дата+URL/скан). У USmile лицензия: `clients/usmile/legal/license/`.
- Присутствие/значения — кодом (наличие блока/CSS/regex/PDF — `parsing-read-pdfs`), каждое = url+дата+evidence.

## Антипаттерны
- ❌ Проверять только цены, игнорируя полноту (лицензии/врачи/работы).
- ❌ Статус «на глаз» без url/evidence.
- ❌ Лицензия/врач без CONFIRMED+источник.
- ❌ Проект клиники без `clinics-presence.json`.

## Применение / TODO
- Готово: стандарт + схема (VALID). Парсер `slug → clinics-presence.json` — реализовать отдельной СВЕЖЕЙ сессией (не в Dumb Zone).
- Кандидат-скилл `/clinic-presence <slug>` (болванка, сбор статусов, gap, completeness, отчёт-матрица). Первый прогон — USmile.

## Sync
`~/.claude/rules/` → 3 аккаунта. Спека/схема — в artvision-data/git.
