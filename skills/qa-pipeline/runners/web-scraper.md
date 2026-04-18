# Runner — Web Scraper

## Применимо к
- Python + Playwright (перехват JSON / DOM парсинг)
- Python + BeautifulSoup/lxml (HTTP + парсинг)
- Python + Scrapy
- Python + SeleniumBase (anti-detect UC mode)

## Фазы

### P0
1. **Lint** — ruff
2. **Type check** — mypy
3. **Unit tests** — парсеры из HTML-fixtures (чистые функции, без сети)
4. **Coverage ≥ 75%**
5. **Security** — bandit
6. **Schema validation** — каждый извлечённый record проходит JSONSchema

### P1
7. **Integration — live smoke** — реальный скрейп 1-2 URL, проверка что данные не пустые
8. **Regression — golden files** — `deepdiff` сравнение с прошлым успешным прогоном
9. **Data freshness** — если последний успешный >7 дней → fail

### P2
10. **Anti-detect** — `bot.sannysoft.com` / `fingerprint.com/bot-detection` — weekly cron
11. **Locator resilience** — запрет на `nth-child`, `xpath с индексами`, обязательны `data-testid` или текстовые

## Критичные проверки

### Стабильность селекторов

✅ Хорошо:
```python
page.locator('[data-testid="doctor-name"]').text_content()
page.get_by_role("heading", name="Расписание")
```

❌ Плохо:
```python
page.locator('.col-md-6:nth-child(3) > div > h2').text_content()  # хрупко
page.query_selector('body > div > div:nth-child(2)')              # ещё хрупче
```

### Перехват JSON > DOM-парсинг

Если сайт делает API-запрос → **перехватывать ответ через `page.on("response")`**, а не парсить верстку. Пример из production `medflex.py`:

```python
async def handle_response(response):
    if "/api/schedule/" in response.url and response.status == 200:
        data = await response.json()
        schedule_cache[filial_id] = data

page.on("response", handle_response)
await page.goto(widget_url)
await page.wait_for_timeout(3000)  # ждём API-запросы
```

Плюсы: нет зависимости от верстки, данные полные и структурированные.
Минусы: нужен реальный браузер (JS выполнение), холодный старт ~5-10 сек.

### Schema validation (обязательно)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["id", "name", "phone"],
  "properties": {
    "id": {"type": "string"},
    "name": {"type": "string", "minLength": 1},
    "phone": {"type": "string", "pattern": "^\\+?[0-9()\\- ]{7,}$"},
    "url": {"type": "string", "format": "uri"},
    "price": {"type": "integer", "minimum": 0}
  }
}
```

### Golden files (regression)

```bash
# Первый прогон — сохранить эталон
PYTEST_GOLDEN_UPDATE=1 pytest tests/regression/

# Последующие — сравнить через deepdiff
pytest tests/regression/
# fail → diff в output, решаем: обновлять golden или фиксить парсер
```

### Data freshness gate

```python
def test_last_scrape_recent():
    last = Path("logs/last_scrape_success.txt").read_text()
    delta = time.time() - float(last)
    assert delta < 7 * 86400, f"Last scrape was {delta/86400:.1f} days ago — stale"
```

### Anti-detect (P2, weekly cron)

```python
def test_not_detected_as_bot():
    with SB(uc=True, headless=False) as sb:
        sb.open("https://bot.sannysoft.com/")
        result = sb.get_text("#webgl-vendor-and-renderer")
        assert "bot" not in result.lower()
```

## Специфика скрейпинга

### Rate limiting / вежливость
- Respect `robots.txt` — скрейпер должен парсить и уважать
- `Crawl-delay` — хоть формально игнорируется многими, соблюдать для избежания банов
- Max 1 req/sec на один домен по умолчанию
- Exponential backoff на 429/5xx

### Stealth
- User-Agent — реалистичный современный Chrome, не "Python/3.14"
- Headers — Accept, Accept-Language, Referer
- Canvas fingerprint, WebGL — `SeleniumBase(uc=True)` решает
- IP — residential proxy для массового скрейпинга (datacenter IP палятся)

### Что нельзя делать в тестах
- НЕ гонять анти-детект на каждом PR (медленно + флакает)
- НЕ скрейпить production на каждом CI — cache HTML-snapshots
- НЕ хранить скрейпенные данные клиентов в git (GDPR)

## Применение к продуктам (примеры)

| Продукт | Технология | Качество | Оценка |
|---------|-----------|----------|--------|
| `medflex.py` (tvorim survey-bot) | Playwright + JSON interception | PASS-WITH-CONDITIONS, 4 фикса = 7h | Подключать можно |
| Direct-Radar (products/) | ? | Не аудирован | TBD |
| SEO Pipeline (products/) | ? | Не аудирован | TBD |

## Gate критерии

**PASS**:
- Все P0 зелёные
- Schema validation 100%
- Golden files совпадают ИЛИ изменения одобрены
- Last successful scrape <7 дней

**FAIL**:
- Парсер возвращает пустые/None ключевые поля
- Schema violation >5% records
- Anti-detect test показывает bot-detected (для scraping targets с защитой)
