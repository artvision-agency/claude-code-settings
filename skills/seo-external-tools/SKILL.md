---
name: seo-external-tools
description: Каталог-роутер внешних SEO-инструментов (форки + pip/npm-зависимости) для всех клиентов Artvision. Вызывать когда задача про кравл сайта, screaming frog альтернативу, SEO-аудит дашборд, sitemap-парсинг, Lighthouse Core Web Vitals, broken links, Google Search Console MCP, Yandex Webmaster API, программатик SEO. Триггеры (рус/eng) — кравл сайта, обход домена, screaming frog, SEO мониторинг, дашборд клиентов, сравнение с конкурентом, GSC, Search Console, Вебмастер Яндекс, индексация Google, индексация Яндекса, sitemap парс, robots.txt парс, log analysis, core web vitals, lighthouse, pagespeed, broken links, битые ссылки, advertools, linkinator, lhci, seonaut, librecrawl.
---

# SEO External Tools — каталог-роутер

> **Когда использовать:** любая SEO-задача для клиента Artvision где нужен внешний инструмент (форк или pip/npm-зависимость), а не наш собственный скрипт из `~/semantic-pipeline/` или `~/artvision-data/scripts/`.
>
> **Принцип:** наши скрипты — основа (Wordstat / Webmaster / Topvisor / hybrid-seo-audit). Внешние инструменты — дополнение там, где у внешнего community лучше покрытие.

## Маршрутизация — фраза пользователя → инструмент

| Триггер | Инструмент | Где запускать | Что вернёт |
|---------|-----------|---------------|------------|
| "кравл сайта", "обход домена", "screaming frog", "техаудит сайта" | **LibreCrawl** (форк) | `~/forks/seo/LibreCrawl/` | Полный кравл на десктопе (open-source альтернатива Screaming Frog) |
| "SEO мониторинг", "дашборд клиентов", "непрерывный аудит" | **seonaut** (форк) | `~/forks/seo/seonaut/` → деплой на VPS | Web-дашборд для всех клиентских сайтов |
| "GSC", "Search Console", "индексация Google", "позиции в Google" | **gsc-mcp-server** (форк) | `~/forks/seo/gsc-mcp-server/` → подключить как MCP | Прямой доступ из Claude Code к GSC API |
| "Вебмастер Яндекс", "индексация Яндекса", "host id" | `~/artvision-data/scripts/webmaster_quality_audit.py` + наш форк gsc-mcp (доработать под Я.Вебмастер) | Bash | JSON с метриками |
| "wordstat", "семантика частотность", "сбор семантики" | `~/semantic-pipeline/wordstat_v4_collector.py` (НАШ — лучше чем yandex-wordstat-mcp 1★) | Bash | CSV с частотностью |
| "sitemap парс", "robots.txt парс", "log analysis", "advertools" | `advertools` (pip) | `python -c "import advertools as adv; ..."` | DataFrame |
| "core web vitals", "pagespeed", "lighthouse" | `lhci` (npm) | Bash | HTML-отчёт + JSON |
| "broken links", "битые ссылки", "linkinator" | `linkinator` (npm) | `linkinator <url>` | Список 404 |

## Стек по слоям

### Уровень 1 — наши скрипты (приоритет)
- `~/semantic-pipeline/` — 70 Python-скриптов (Wordstat, кластеризация, ТЗ, аудит)
- `~/artvision-data/scripts/hybrid-seo-audit.py` — основной аудит-pipeline
- `~/artvision-data/scripts/webmaster_quality_audit.py` — Я.Вебмастер
- `~/artvision-data/scripts/topvisor_serp.py` — позиции (с защитой через `pre-bash-topvisor-guard.sh`)

### Уровень 2 — pip/npm-зависимости (используем как библиотеки)
- `advertools 0.17+` — sitemap, robots, кравлер, SERP, log analysis
- `@lhci/cli 0.15+` — Lighthouse CI для Core Web Vitals
- `linkinator 7.6+` — broken links checker

### Уровень 3 — форки (модифицируем под наши задачи)

**Группа A (модифицируем):**

| Форк | Звёзд | Зачем форк |
|------|------|------------|
| [`LibreCrawl`](https://github.com/justtrance-web/LibreCrawl) | 601★ | Допилить под Tilda/MODX/Bitrix-extractors, экспорт в наш формат |
| [`seonaut`](https://github.com/justtrance-web/seonaut) | 696★ | Развернуть на VPS как непрерывный мониторинг всех клиентов |
| [`gsc-mcp-server`](https://github.com/justtrance-web/gsc-mcp-server) | 11★ | Внедряем (вердикт round_table 2026-05-01: ВНЕДРЯТЬ С ДОРАБОТКОЙ — secret-manager, retries, Docker health-check). Расширить до Yandex.Webmaster MCP (публично нет!) |
| [`yandex-wordstat-mcp`](https://github.com/justtrance-web/yandex-wordstat-mcp) | 1★ | **НЕ ВНЕДРЯЕМ** (вердикт round_table 2026-05-01) — устаревший API v2, без тестов. Хранится как референс |

**Группа B (изучаем, переносим идеи в наши скиллы):**

| Форк | Звёзд | Что взять |
|------|------|-----------|
| [`JeffLi1993/seo-audit-skill`](https://github.com/justtrance-web/seo-audit-skill) | 301★ | Структура промптов для Claude Code SEO-skill |
| [`seo-skills/seo-audit-skill-1`](https://github.com/justtrance-web/seo-audit-skill-1) | 201★ | **108 audit rules** — перенести в наш чеклист |
| [`Horosheff/google-yandex-seo-skill`](https://github.com/justtrance-web/google-yandex-seo-skill) | 21★ | Единственный публичный Google+Yandex skill — изучить структуру |

## Use cases — сценарии вызова

### "Сделай SEO-аудит synamica.ru" / любой клиентский домен
1. Базовый: `~/artvision-data/scripts/hybrid-seo-audit.py <domain>` — наш pipeline
2. Дополнить: `lhci collect --url=https://<domain>` — Core Web Vitals
3. Дополнить: `linkinator https://<domain> --recurse` — broken links
4. Структурный: LibreCrawl (через GUI или CLI форка)
5. Long-running: добавить домен в seonaut на VPS

### "Проверь индексацию Google для клиента"
1. Подключить gsc-mcp-server как MCP в `~/.claude.json` (после доработки)
2. Альтернатива: `python -m advertools.serp` через Bash
3. Альтернатива: `joshcarty/google-searchconsole` Python-обёртка (244★)

### "Собери семантику по теме X"
1. **Только наш скрипт:** `~/semantic-pipeline/wordstat_v4_collector.py`
2. Кластеризация: `~/semantic-pipeline/seo_clusterer_v2.py`
3. ТЗ: `~/semantic-pipeline/tz_generator_v6.py`
4. ❌ НЕ использовать `yandex-wordstat-mcp` (вердикт round_table)

### "Мониторь sitemap клиента ежедневно"
1. `advertools.sitemap_to_df(url)` → сравнение vs предыдущий день
2. Cron на наш VPS

## Правила безопасности

- Перед внедрением форка с <50★ — `mcp__llm-consilium__round_table` (правило `tool-adoption-proof.md`)
- Для gsc-mcp + wordstat-mcp round_table уже выполнен 2026-05-01 — см. `~/forks/seo/ROUND_TABLE_2026-05-01.md`
- Все форки клонированы под `justtrance-web` GitHub org
- Никогда не публиковать клиентские данные в форках (PR в upstream — только generic improvements)

## Связанные инструменты

- `/seo-master` — главный SEO-роутер Artvision (наш)
- `/local-seo`, `/linkbuilding`, `/parasitic-seo`, `/schema-markup`, `/programmatic-seo` — наши доменные skill
- `/seo-domain-diff`, `/text-factors-audit`, `/behavioral-factors-audit`, `/commercial-factors-audit`, `/link-factors-audit`, `/seo-factors-audit` — аудиторы

## Версии (на 2026-05-01)

```
advertools 0.17.2 (pip)
@lhci/cli 0.15.1 (npm)
linkinator 7.6.1 (npm)
```

## Изменения

- 2026-05-01 — создан skill, форки A+B клонированы, pip/npm зависимости установлены, round_table проведён.
