---
name: seo-domain-diff
description: "Сравнительный SEO-аудит двух доменов (новый vs legacy / vs конкурент) по постулатам Artvision R1-R10 + seo-master + tfidf-clustering. Применяется при миграции сайта, редизайне, потере позиций после релиза. Триггеры: 'сравни сайт X vs Y', 'аудит миграции', 'что есть у legacy чего нет у нового', 'domain diff', 'сравнение доменов', 'миграция сайта', 'новый сайт упал в позициях', 'верни блоки старого сайта'."
---

# SEO Domain Diff — сравнительный аудит двух доменов

## Когда применять

- Миграция сайта (старый домен → новый, или редизайн)
- Падение позиций после релиза нового сайта
- Решение «что вернуть из legacy» / «чего не хватает на новом»
- Сравнение с прямым конкурентом

## ОБЯЗАТЕЛЬНО — наши постулаты (cross-check всех правил)

| Источник | Применить |
|----------|-----------|
| `~/artvision-data/knowledge/seo/rules.md` | R1-R10 (X-Robots, factcheck, robots backup, SERP-data, viewport+canonical, дубли, мискласс, гео, доставка РФ, инструменталка) |
| `~/.claude/skills/seo-master/SKILL.md` | Robots 10, Sitemap 8, CWV, Mobile First, Title 4U, H1×1, H2≥5, LSI 5-6/1000, ВЧ max 10-15, JSON-LD, TF-IDF |
| `~/artvision-data/.claude/rules/tfidf-clustering.md` | TF-IDF биграммы+триграммы, Hard/Soft кластеры, обе ПС |
| `~/artvision-data/.claude/rules/factcheck.md` | CONFIRMED/UNCONFIRMED/WRONG, 2+ источника |
| `~/artvision-data/.claude/rules/yandex-api.md` | Wordstat/Direct/Webmaster/Метрика — через API из tokens.json |
| `~/artvision-data/.claude/rules/scraping.md` | WebFetch → Playwright → WebSearch (антибот эскалация) |

## Pre-flight (ОБЯЗАТЕЛЬНО запросить у пользователя)

1. **Регион SERP** (R4): lr=225 (РФ) / lr=213 (МСК) / lr=2 (СПб) / иной — приоритеты
2. **Статус legacy** — индексируется (риск каннибализации) или закрыт от индексации?
3. **Папка клиента** — есть `clients/[name]/`?
4. **Доступы** — Я.Метрика и Я.Вебмастер (tokens.json или счётчик?)

## Workflow (8 этапов, cross-check после каждого)

### Этап 1. Инструментальный краул обоих доменов (R10)
```bash
# Screaming Frog headless или curl + lxml
python3 ~/artvision-data/scripts/hybrid-seo-audit.py --url https://NEW_DOMAIN
python3 ~/artvision-data/scripts/hybrid-seo-audit.py --url https://LEGACY_DOMAIN
```
Собрать: title, h1, h2, description, canonical, viewport, status, размер, схема URL.

### Этап 2. Я.Метрика + Вебмастер API (R10)
- Метрика API: трафик, bounce, глубина — на оба счётчика (если есть)
- Вебмастер API: показы, клики, позиции, ошибки индексации
- Сохранить в `clients/[name]/seo/diff/api-data-YYYY-MM-DD.json`

### Этап 3. SERP-анализ конкурентов (R4 — БЕЗ ЭТОГО НЕТ ВЫВОДОВ)
Для каждого региона из preflight:
- Топ-10 кластеров запросов (Wordstat API)
- WebSearch + Topvisor (НЕ скрейп Яндекса) → ТОП-10 SERP
- Кто на каких позициях, что в title/description/сниппете
- gap-анализ: чего нет у нас vs конкурентов

### Этап 4. DOM-diff главной + ключевых страниц
```python
# Playwright + BeautifulSoup
# Извлечь: блоки секций (h2 + ближайший контейнер), CTA, формы, отзывы, видео, schema
# Сравнить: какие блоки есть на legacy, каких нет на новом
```
Output: таблица «блок | legacy | new | приоритет вернуть»

### Этап 5. Чеклист seo-master (на оба домена)
- [ ] R5: viewport + canonical (ПЕРВЫМ — отсутствие = пессимизация)
- [ ] Title 4U (Useful, Urgent, Unique, Ultra-specific)
- [ ] H1 один на странице
- [ ] H2 ≥ 5 на странице
- [ ] Description 140-160
- [ ] Robots.txt (10 правил из seo-master)
- [ ] Sitemap.xml (8 правил)
- [ ] Schema JSON-LD (Organization, Product, Breadcrumb)
- [ ] CWV: LCP <2.5s, INP <200ms, CLS <0.1
- [ ] Mobile First viewport ≤ 375px

### Этап 6. R6 + R7 — дубли и мискласс
- Дубли текста на подкатегориях (одинаковый текст ≥ 80% → пессимизация кластера)
- Товары соответствуют категории (топливные в тормозных = ⚠️)

### Этап 7. TF-IDF на топ-страницах (обе ПС)
- Юниграммы + биграммы + триграммы
- Русские стоп-слова
- MISSING / UNDERUSED / OVERUSED / UNIQUE для каждой страницы
- Hard/Soft кластеризация (пересечение SERP)

### Этап 8. R9 — «доставка по РФ» и гео-маркеры (R8)
- Сниппеты ТОП-10: 3+ конкурентов пишут «доставка по России» → добавить нам
- Гео в title/h1 если локальный бизнес

## Output (CAMEO стиль)

`clients/[name]/seo/diff/REPORT-YYYY-MM-DD.html` — HTML дашборд:
1. Executive summary: 5 главных gap-ов
2. Таблица «блок legacy vs new» (с скриншотами)
3. SERP gap-анализ
4. R1-R10 чеклист «применил/пропустил/не применимо» для каждого этапа
5. Roadmap: P0 (критичные пессимизаторы) → P1 (восстановление блоков) → P2 (TF-IDF дополнения)
6. Источники (URL + дата + CONFIRMED/UNCONFIRMED маркировка)

## Anti-patterns (НЕ ДЕЛАТЬ)

- ❌ WebFetch на мета-теги → теряет `<head>`. Только `curl -sL | grep`
- ❌ Скрейп Яндекс SERP → блок капчи. Только Topvisor / WebSearch с site:
- ❌ Сторонние SaaS (SEMrush/Ahrefs/Serpstat) — только наши пайплайны
- ❌ «Похоже что упало» без Метрики/Вебмастера — это домыслы (R10)
- ❌ Анализ без региона — R4 без региона = ничто

## Cross-check в конце

Таблица в финальном отчёте:
| Постулат | Применил | Где в отчёте |
|----------|----------|--------------|
| R1 X-Robots | ✅/➖ | этап 1 |
| R4 SERP по региону | ✅ | этап 3 |
| R5 viewport+canonical | ✅ | этап 5 |
| ... | | |

## Прецедент

Создан 2026-05-01 в сессии Madwave (madwave.ru ↔ legacy.madwave.ru). Первый кейс — пилот.
