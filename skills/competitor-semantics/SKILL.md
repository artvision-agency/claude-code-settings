---
name: competitor-semantics
description: Расширить семантику клиента НА ОСНОВЕ конкурентов (не маски из головы) — structure-scrape конкурентов → gap → Wordstat-валидация → кластер-карта. Работает без keys.so/DataForSEO (через curl-структуру). Триггеры — семантика от конкурентов, competitor semantics, расширить семантику по конкурентам, gap семантика, кластеры от конкурентов, competitor-semantics, чего нет у клиента из конкурентов, семантический gap.
---

# Семантика от конкурентов (competitor-derived)

> Против граблей #23/#26: НЕ маски из головы, НЕ прокси-данные, НЕ гадание. Реальные кластеры что таргетируют конкуренты. Детали — `~/.claude/rules/topvisor-ops.md`, `semrush-ops.md`, `tfidf-clustering.md`.

## Вызов
`/competitor-semantics <client_domain> <competitor1,competitor2,...>`

## Метод (по порядку)
1. **Текущее ядро клиента** — из Topvisor (`get/keywords_2/keywords`) или queries.txt.
2. **Ключи конкурентов** (по приоритету источника):
   - keys.so (Яндекс organic) — если токен есть (точнее всего для RU). **Нет токена → шаг 2б.**
   - SEMrush organic/top_pages (`scripts/semrush_top_pages.py`) — Google, RU-покрытие тонкое.
   - **2б Fallback (всегда работает без токенов):** `curl <competitor>/sitemap.xml + /uslugi/ + /services/` → собрать H1/title/URL service-страниц → их реальные коммерческие кластеры (типы работ/услуг что они таргетируют).
3. **Gap:** какие кластеры/ключи есть у конкурентов и НЕТ у клиента.
4. **Wordstat-валидация** gap-ключей (Direct API v4, batch≤10, GeoID региона) → отсев shows=0. Только спрос>0.
5. **SERP-overlap кластеризация** (если DataForSEO-токен есть → `/seo-cluster`; нет → intent-based группировка + пометка «SERP-валидация pending»).
6. **Загрузка в Topvisor:** `add/keywords_2/keywords` с `to_id`+`name` по одному (`topvisor-ops.md`).

## Жёсткие правила
- НЕ генерировать ключи масками из своих знаний ниши как ОСНОВУ — только как дополнение к competitor-derived.
- Каждый gap-ключ с частотностью (Wordstat) + откуда (какой конкурент таргетирует).
- Различать B2B-формулировки с нулевой частотностью (часто «аутсорсинг/опт/для X» = 0 показов → не семантика, а отдельная посадочная).

## Связано
`tfidf-clustering.md` (SERP-overlap hard/soft), `seo-presale-audit-workflow.md` Шаг 3, `/seo-cluster`, `/seo-master`, self-corrections #23/#26.
