---
name: seo-presale-audit
description: Полный presale SEO-аудит клиента по канону Artvision — строго по seo-audit-spec.md, в дизайн-системе клиента, без хендролла. Оркестратор Шаг 0→6 (спек+дизайн → data-precheck → SF crawl → семантика competitor-derived → Lighthouse CWV → сборка §1-§6 → деплой+скриншот). Триггеры — seo presale аудит, presale аудит клиента, полный seo аудит, аудит для кп, seo-presale-audit, сделай аудит клиенту, presale seo.
---

# SEO presale-аудит — оркестратор

> Главный анти-грабли скилл (self-corrections #23/#24): не собирать из головы, не дефолтить тёмную тему, не врать «Pending» без проверки. Детальный порядок — `~/.claude/rules/seo-presale-audit-workflow.md` (читать его).

## Вызов
`/seo-presale-audit <slug> <domain>` (напр. ds-lab https://ds-lab.ru)

## ЖЁСТКИЙ порядок (не пропускать, не менять местами)

**Шаг 0 — КАНОН (первым!):**
- `Read templates/seo-audit-spec.md` (структура 7 секций + TOC). Медицина → `dental-clinic-blueprint.md` §XII.
- Извлечь дизайн-систему клиента: `curl <site> + styles.css | grep '#hex' + font-family + hero-img`. НЕ тёмная тема (`analyzed-project-design-system.md`).

**Шаг 1 — DATA-PRECHECK** (что реально доступно, чтобы не гадать):
- Topvisor: `get/projects_2/projects {show_searchers:1}` → searchers есть? позиции снимались? (`topvisor-ops.md`)
- SEMrush сессия жива? токены keys.so/DataForSEO/PSI есть? доступ к Метрике клиента? → карта «собрано / Pending(почему)».

**Шаг 2 — CRAWL:** `scripts/seo/run-seo-pipeline.sh <slug> <domain>` → читать sf-out/ (статусы, 4xx, дубли title, пустые canonical) csv-парсом.

**Шаг 3 — СЕМАНТИКА (competitor-derived, не маски):** текущее ядро Topvisor → Wordstat expand+отсев shows=0 → gap от структуры конкурентов (curl sitemap+/uslugi/) → Wordstat-валидация gap → кластер→посадочная карта. (`semrush-ops.md` fallback, `topvisor-ops.md` add `to_id`).

**Шаг 4 — CWV:** `lighthouse https://<d>/ --only-categories=performance --form-factor=mobile --chrome-flags=--headless=new` (локально, PSI-токен не нужен).

**Шаг 5 — КОНКУРЕНТЫ:** WebSearch + **WebFetch каждого сайта** (не сниппеты): лаборатория vs клиника, услуги, прайс, B2B, digital/срок-УТП. Чужие «ТОП-N РФ» = маркетинг.

**Шаг 6 — СБОРКА+ДЕПЛОЙ:** HTML строго §1-§6+TOC, в дизайн-системе клиента (hero-фото+overlay, иконки-метрики, SVG-секции). §5 тариф 3 пакета (мед 105/135/175К). §6 план 1мес 4 направления. Деплой `artvision.pro/_priv-<slug>-<date>/` → curl 200 → **скриншот-верификация (Read png)** → deploy-URL первой строкой.

## Антипаттерны
Структура из головы · тёмная тема · «Pending» без precheck · семантика масками · конкуренты по сниппетам · деплой без скриншота · file:// вместо live URL.

## Связано
`seo-presale-audit-workflow.md`, `topvisor-ops.md`, `semrush-ops.md`, `templates/seo-audit-spec.md`, `/seo-master`, `/seo-cluster`, `/topvisor-init`, `/presale-kp`.
