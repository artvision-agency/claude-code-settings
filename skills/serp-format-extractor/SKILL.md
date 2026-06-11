---
name: serp-format-extractor
description: "Извлекает HTML-структуру top-3 SERP (H1/H2/H3 cascade, word count, изображения, FAQ, schemas) → JSON-каркас для content-writer. Применять ПЕРЕД написанием статьи. Триггеры: 'serp format', 'top 3 структура', 'extract top serp', 'каркас из serp', 'top-3 html шаблон', 'формат конкурентов', 'serp каркас', 'извлечь структуру топ', 'шаблон из топа'."
user-invokable: true
argument-hint: "<keyword> [--region=msk] [--engine=google|yandex] [--out=path.json]"
allowed-tools: [Read, Write, Edit, Bash, WebSearch, WebFetch, Grep, Glob]
metadata:
  category: seo
  version: "0.1.0"
  pairs-with: [content-writer, seo-content-brief, seo-cluster]
---

# SERP Format Extractor

Извлекает HTML-структуру топ-3 страниц поисковой выдачи и формирует JSON-каркас (рекомендованный H1/H2/H3 cascade, целевой word count по секциям, наличие FAQ, schema-типы). Каркас передаётся в `content-writer` как input — статья получается в формате, который Google/Яндекс уже наградили в топе.

## Когда применять

- Перед написанием новой SEO-статьи (info-кластер)
- Перед редизайном коммерческой посадочной по конкурентам в топе
- Когда нужно понять «какой формат тут работает» (long-form vs listicle vs FAQ-heavy)
- Антипаттерн: НЕ применять для уникальных landing pages где нет аналогов в SERP

## Когда НЕ применять

- Брендовые запросы (топ-3 = сам клиент)
- Транзакционные коммерческие (топ = маркетплейсы/агрегаторы — не наша модель)
- Очень узкие low-volume запросы (нет валидной выборки)

## Pipeline

```
1. WebSearch (или Topvisor API для Яндекса с регионом) → top-3 URLs
2. Fetch HTML каждого URL (WebFetch для статики, Playwright fallback для JS-SPA)
3. parse_dom.py — BeautifulSoup → DOM-анализ:
   - H1, H2 cascade с word count per section
   - H3 nesting
   - Word count total + intro length
   - Image count + alt-плотность
   - FAQ block presence (FAQPage schema + <details>/accordion patterns)
   - Schema.org types via JSON-LD parsing
   - External/internal links count
4. build_template.py — синтез JSON-каркаса:
   - Median word count per section (устойчивее среднего)
   - Union of unique H2 topics (по lemma matching)
   - Recommended schemas
5. Output → JSON в --out (default: ~/.claude/cache/serp-format/<keyword-hash>.json)
6. Передача в content-writer как input
```

## Использование

### CLI прямой запуск

```bash
python3 ~/.claude/skills/serp-format-extractor/scripts/parse_dom.py \
  --html article.html --out section-1.json
```

### Полный pipeline (когда extract_top3.py будет готов)

```bash
python3 ~/.claude/skills/serp-format-extractor/scripts/extract_top3.py \
  "имплантация зубов в спб" --region=spb --engine=yandex \
  --out=~/.claude/cache/serp-format/implant-spb.json
```

### Передача в content-writer

```bash
# 1. Извлечь каркас
serp-format-extractor "ключ" > template.json

# 2. Скормить content-writer
cat template.json | content-writer --keyword "ключ" --template-from-stdin
```

## JSON-формат каркаса (output)

```json
{
  "keyword": "имплантация зубов в спб",
  "region": "spb",
  "engine": "yandex",
  "collected_at": "2026-05-21T10:00:00Z",
  "recommended_structure": {
    "h1_pattern": "Имплантация зубов в Санкт-Петербурге — [USP]",
    "intro_length_words": 80,
    "total_target_words": 1850,
    "sections": [
      {
        "h2": "Что такое имплантация",
        "word_count_target": 220,
        "h3_count": 2,
        "has_image_recommended": true
      },
      {
        "h2": "Этапы лечения",
        "word_count_target": 380,
        "h3_count": 4,
        "has_image_recommended": true
      },
      {
        "h2": "Цены",
        "word_count_target": 180,
        "h3_count": 0,
        "has_image_recommended": false
      }
    ],
    "faq_recommended": true,
    "faq_questions_target": 8,
    "schemas": ["Article", "FAQPage", "MedicalProcedure"],
    "internal_links_target": 12,
    "external_links_target": 3
  },
  "top_3_analysis": [
    {"url": "https://...", "word_count": 1920, "h2_count": 7, "has_faq": true, "schemas": [...]},
    {"url": "https://...", "word_count": 1740, "h2_count": 6, "has_faq": true, "schemas": [...]},
    {"url": "https://...", "word_count": 2010, "h2_count": 8, "has_faq": false, "schemas": [...]}
  ]
}
```

## Anti-captcha и fallback

- **Google:** WebSearch (главный путь). Если заблочен — bing.com или yandex.com (если регион не критичен)
- **Яндекс:** Topvisor API (с регионом) → `tokens.json → topvisor.api_key`. Прямой curl yandex.ru/search всегда даёт captcha (см. memory `feedback_yandex_serp_captcha_use_google_fallback.md`)
- **JS-SPA сайты:** WebFetch не рендерит → fallback на Playwright (`agent-browser` skill)
- **Кэш:** JSON-каркасы храним 7 дней в `~/.claude/cache/serp-format/<sha1-keyword>.json` — повторный запуск по тому же ключу не fetch'ит заново

## Интеграция с другими skills

| Skill | Связь |
|-------|-------|
| `seo-content-brief` | Делает gap analysis (что писать). Каркас от serp-format-extractor дополняет: какой формат |
| `seo-cluster` | Делает SERP overlap для кластеризации. Каркас даёт детали по 1 ключу из кластера |
| `seo-competitor-pages` | vs/alternative страницы — не каркас, а конкурентная позиция |
| `content-writer` | Принимает JSON-каркас как input → пишет статью в формате топ-3 |
| `factcheck` | Прогон финальной статьи перед deploy (CONFIRMED/UNCONFIRMED маркировка) |

## Стандарты Артвижн

- Числа в JSON — median (устойчивее к outlier'ам), не mean
- Все URL в top_3_analysis — реальные с HTTP 200 на момент collected_at
- Если top-3 даёт <2 валидных конкурентов (Wikipedia/Reddit отфильтрованы) — output помечен `"confidence": "low"`, требует ручной верификации
- Лог fetch'ей: `~/.claude/logs/serp-format-extractor.log`
- Использует `proven-tools-first` принцип: BeautifulSoup 4 + advertools 0.17 (уже установлены)
- Региональность для Яндекса обязательна (см. правило `feedback_topvisor_ui_required_for_region.md`)

## Антипаттерны

- ❌ Слепое копирование структуры одного топа (нужна triangulation от 3 источников)
- ❌ Считать word_count как mean — outlier 5000-слов руинит median; используем median
- ❌ Рекомендовать FAQPage schema если нет ни одного top-3 с FAQ — это hallucination
- ❌ Игнорировать region для Яндекса — топ-3 в Москве и СПб разные

## Файлы

```
~/.claude/skills/serp-format-extractor/
├── SKILL.md                      # этот файл
├── scripts/
│   ├── parse_dom.py              # WORKING — DOM extraction из HTML файла (BeautifulSoup)
│   ├── extract_top3.py           # STUB — WebSearch/Topvisor + fetch top-3 URLs
│   └── build_template.py         # STUB — median synthesis 3 анализов → JSON-каркас
└── examples/
    └── example-output.json       # Эталон output для content-writer
```

## Кэш и логи

- Кэш TTL: 7 дней, путь `~/.claude/cache/serp-format/<sha1-of-keyword+region>.json`
- Лог: `~/.claude/logs/serp-format-extractor.log` — записи о fetch'ах, ошибках, cache hit/miss
- Очистка кэша: `rm -rf ~/.claude/cache/serp-format/` (безопасно, регенерится)

## Source-проверка перед adopt (proven-tools-first)

Перед написанием скилла исследованы готовые инструменты:
- **agniiva/Content-Brief-Generator-SERP** — закрытый, использует SerpAPI + OpenAI GPT-4o (платное), не вписался в free Artvision stack
- **ecoron/SerpScrap** — есть Chrome headless + lxml, перебор для нашего usecase (мы используем WebSearch + Topvisor)
- **advertools** (Elias Dabbas) — `crawl()` уже умеет H1/H2/title extract в pandas DataFrame, ИСПОЛЬЗУЕТСЯ как baseline в `parse_dom.py` для batch-сравнения
- **Thruuu Heading Extractor** — UI-only, нет API, не подходит

Решение: пишем тонкий BeautifulSoup-слой поверх установленного advertools, синтез JSON делаем сами (специфика Artvision: median + region + cache).
