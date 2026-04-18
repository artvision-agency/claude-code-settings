# QA Starter — Web Scraper (Python + Playwright + SeleniumBase)

Тестовая обвязка для проектов, где мы вытаскиваем структурированные
данные со сторонних сайтов (маркетплейсы, агрегаторы, каталоги, SERP).

## Применение

```bash
cp -r ~/.claude/templates/qa-starter/web-scraper/. ./
make install   # pip + playwright install chromium
make test      # unit + schema + regression (fast)
```

## Структура

```
web-scraper/
├── README.md
├── requirements-dev.txt
├── pytest.ini
├── Makefile
├── tests/
│   ├── conftest.py                    # browser, cassette_dir, golden_dir fixtures
│   ├── unit/
│   │   ├── test_parsers.py            # чистые парсеры (HTML string → dict)
│   │   └── test_freshness.py          # data age <7 days guard
│   ├── integration/
│   │   ├── test_live_extraction.py    # smoke 1-2 URL (canary, не production run)
│   │   └── fixtures/                  # HTML snapshots для регрессии
│   ├── schema/
│   │   ├── schema.json                # JSONSchema extracted record
│   │   └── test_schema_validation.py
│   ├── regression/
│   │   ├── test_golden_files.py       # deepdiff vs golden JSON
│   │   └── golden/                    # последний known-good прогон
│   └── stealth/
│       └── test_anti_detect.py        # SeleniumBase UC vs sannysoft
└── .github/workflows/scraper-tests.yml  # headless fast, weekly headful
```

## Ключевые концепции

### 1. HTML fixtures
Снапшоты живого HTML лежат в `tests/integration/fixtures/*.html`. Один
integration-тест сохраняет свежий snapshot → unit и regression тесты
переиспользуют его **без сети**. Это делает 95% тестов быстрыми и
детерминированными.

### 2. Schema validation
Каждая извлечённая запись прогоняется через JSONSchema
(`tests/schema/schema.json`). Ловим:
- `price` вернулся как строка `"8 500 р"` вместо int,
- `url` без схемы `https://`,
- `telephone` с буквами,
- пустой `name`.

Схема — single source of truth полей. Меняются поля в БД — меняется
схема — падают тесты. Не silent.

### 3. Golden files
`tests/regression/test_golden_files.py` сериализует каждую
распарсенную запись в `golden/<name>.golden.json`. При следующих
прогонах `deepdiff` показывает конкретные поля которые разошлись.

**Обновление golden-файлов** после целевого изменения:
```bash
make golden-update  # или PYTEST_GOLDEN_UPDATE=1 pytest tests/regression
```

### 4. Anti-detect (stealth)
`SeleniumBase` в UC-mode против `bot.sannysoft.com`. Запускается **ТОЛЬКО
headful** (xvfb в CI). Headless всегда падает на sannysoft — это
нормально и не диагностично.

Порог — не больше 30% failed checks. Выше → апдейтим stealth-конфиг, а
не тест.

### 5. Data freshness
`test_freshness.py` падает если последний полный scrape > 7 дней
(`data/last_run.json.completed_at`). Ежедневный cron в CI = лимит «наши
данные никогда не протухают незаметно».

### 6. Locator resilience
Правило в парсерах:
1. **Preferred:** `data-testid` атрибут.
2. **Fallback:** text content / semantic tag (h1, .price).
3. **Запрещено:** `nth-child`, абсолютные XPath, class-цепочки длиной >2.

Пример fallback в `tests/unit/test_parsers.py::test_parse_product_fallback_to_h1_and_class`.

## Чего НЕ проверяем этими тестами

- **Production scraping** больших объёмов — это отдельный CLI/worker, не pytest.
- **Прокси rotation, captcha solving, IP-пулы** — уровень deploy/infra.
- **Rate limits конкретного сайта** — отдельные dry-run с логами в stage.
- **Юридика скрейпа** (ToS, robots.txt, GDPR) — ручной аудит в legal/.
- **Anti-detect на конкретном защищённом сайте** (Cloudflare Turnstile,
  PerimeterX, DataDome) — там нужен платный solver, не юнит-тесты.

## Матрица признанности инструментов

| Tool | Stars (2026-04-18) | Роль | Verdict |
|------|------:|------|---------|
| `pytest` | 12k | runner | Must-have |
| `playwright-python` + `pytest-playwright` | 12k + 543 | live-scrape, headless | Must-have E2E |
| `SeleniumBase` | 12.5k | stealth / anti-detect UC mode | Лучшее для anti-detect в 2026 |
| `beautifulsoup4` + `lxml` | — | HTML parsing | Старые, но живые, быстрые |
| `jsonschema` | 4.5k | schema validation | Стандарт индустрии (Draft 2020-12) |
| `deepdiff` | 2.1k | golden-file diff | Точный dict/list diff с понятным output |
| `tenacity` | 6.7k | retries в live-scrape | Де-факто стандарт retry в Python |

## CI/CD

`.github/workflows/scraper-tests.yml`:
- **fast lane** (каждый push/PR) — unit + schema + regression, headless, <2 мин.
- **integration** — smoke 1-2 URL, headless, на main.
- **stealth** — weekly cron, headful через xvfb, только для anti-detect.

## Связка с остальными QA-templates

Этот template **дополняет**, не заменяет `python/`. Если в проекте есть
и HTTP API, и scraping worker — примени оба:

```bash
cp -r ~/.claude/templates/qa-starter/python/. ./
cp -r ~/.claude/templates/qa-starter/web-scraper/. ./
```
