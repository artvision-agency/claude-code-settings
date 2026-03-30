---
name: geo-audit
description: >-
  GEO-аудит: проверка присутствия бренда в ответах AI-моделей (ChatGPT, Claude, Perplexity, Gemini).
  Запускает скрипт geo_audit.py, анализирует результаты, даёт рекомендации по улучшению видимости.
  Триггеры: geo аудит, geo audit, ai видимость, видимость в ai, ai search, ai поиск,
  как видят ai, gео оптимизация, aivision аудит.
argument-hint: --brand "Brand" --domain site.ru --queries "q1,q2,q3"
user-invocable: true
allowed-tools: Read Write Edit Bash Glob Grep Agent WebSearch WebFetch
---

# GEO-аудит: видимость бренда в AI-моделях

## WORKFLOW

### 1. Pre-check: сбор данных о клиенте

Прочитать конфиг клиента для определения бренда, домена и ниши:

```bash
# Найти config.yaml клиента
find /Users/antonk/artvision-data/clients/ -name "config.yaml" | head -20
```

Из config.yaml извлечь:
- `brand` — название бренда
- `domain` — домен сайта
- `niche` / `industry` — ниша (для генерации запросов)

Если аргументы переданы напрямую (--brand, --domain, --queries) — использовать их.

### 1.5. Technical GEO Pre-check (NEW — robots.txt + LLMS.txt + Schema)

**Запускать ПЕРЕД опросом AI-моделей — параллельно с query selection.**

```bash
# 1. Проверка robots.txt на AI-краулеров (14 ботов)
DOMAIN="site.ru"
curl -sL "https://$DOMAIN/robots.txt" | grep -iE \
  'GPTBot|ChatGPT-User|ClaudeBot|PerplexityBot|Googlebot-Extended|CCBot|cohere-ai|Applebot-Extended|Bytespider|Amazonbot|anthropic-ai|Google-Extended|FacebookBot|meta-externalagent'
# Если бот заблокирован (Disallow) — CRITICAL finding
# Если robots.txt отсутствует — WARNING (все краулеры допущены, но нет контроля)
```

```bash
# 2. Проверка LLMS.txt (новый стандарт — llms.txt, llms-full.txt)
curl -sI "https://$DOMAIN/llms.txt" | head -5
curl -sI "https://$DOMAIN/.well-known/llms.txt" | head -5
# 200 = есть, 404 = нет (рекомендовать создать)
```

```bash
# 3. Schema.org проверка (Speakable, FAQPage, HowTo)
curl -sL "https://$DOMAIN" | grep -oiE '"@type"\s*:\s*"(Speakable|FAQPage|HowTo|Organization|LocalBusiness|Product)"'
# Speakable — приоритет для голосовых AI и AI Overviews
```

```bash
# 4. Freshness signals
curl -sL "https://$DOMAIN" | grep -oiE '(article:modified_time|dateModified|lastmod)' | head -5
```

**Результат:** таблица `Technical GEO Readiness` с ✅/❌ по каждому пункту.

### 2. Query selection

**Если запросы переданы** (`--queries "q1,q2,q3"`) — использовать их напрямую.

**Если запросы НЕ переданы** — сгенерировать 10-15 релевантных запросов:
1. Использовать WebSearch для поиска популярных запросов в нише клиента
2. Включить разные типы запросов:
   - Информационные: "как выбрать [продукт]", "лучшие [услуги] в [городе]"
   - Коммерческие: "купить [продукт]", "[услуга] цена"
   - Навигационные: "[бренд] отзывы", "[бренд] контакты"
   - Сравнительные: "[бренд] vs [конкурент]", "альтернативы [бренд]"
3. Показать сгенерированные запросы пользователю перед запуском

### 3. Запуск скрипта

```bash
python3 /Users/antonk/artvision-data/scripts/geo_audit.py \
  --brand "Brand Name" --domain site.ru \
  --queries "query1,query2,query3" \
  [--config scripts/geo_audit_config.json]
```

Скрипт опрашивает 4 AI-модели через API (tokens.json):
- **Claude** (Anthropic API) — claude-sonnet
- **GPT-4o** (через OpenRouter)
- **Gemini 2.0 Flash** (Google Generative AI)
- **DeepSeek** (OpenAI-compatible API)

Output: HTML dashboard + JSON data в `output/` directory.

### 4. Анализ результатов

Прочитать output JSON и HTML, сформировать сводку:

- **GEO Visibility Index (0-100)** — процент запросов, где бренд упомянут хотя бы одной моделью
- **Breakdown по моделям** — какие модели упоминают бренд, какие нет
- **Breakdown по запросам** — какие запросы триггерят упоминание бренда
- **Конкуренты** — кто упоминается вместо бренда клиента
- **Контекст упоминаний** — в каком тоне и контексте бренд представлен

### 4.5. Параллельные агенты (NEW — 4 агента вместо 1)

При наличии ресурсов запускать **4 параллельных агента** через Agent tool:

| Агент | subagent_type | Задача |
|-------|---------------|--------|
| GEO Technical | `seo-analyzer` | robots.txt AI-краулеры, LLMS.txt, Schema, Speakable, freshness |
| GEO Content | `seo-analyzer` | FAQ-блоки, conversational queries (15-30 слов), direct answer paragraphs |
| GEO Brand Visibility | `general-purpose` | Ручные запросы к ChatGPT/Perplexity/Gemini через WebSearch (нужен Bash) |
| GEO Competitive | `research-analyst` | Конкуренты в AI-ответах: кто появляется, почему, что у них есть |

Каждый агент возвращает свою секцию отчёта → объединить в финальный документ.

### 5. Рекомендации

На основе результатов дать конкретные action items:

**Контентные gaps:**
- Какие темы/запросы не покрыты контентом на сайте
- Какие страницы нужно создать или обновить
- Какие вопросы клиентов остаются без ответа

**Сигналы авторитетности:**
- Schema.org разметка (Organization, LocalBusiness, Product, FAQ)
- Отзывы и рейтинги на внешних площадках
- Экспертный контент (авторские статьи, исследования)
- E-E-A-T сигналы (опыт, экспертиза, авторитетность, доверие)

**Присутствие на платформах:**
- Wikipedia / Wikidata
- Профессиональные каталоги и справочники
- Яндекс.Карты, 2ГИС, Google Maps
- Отраслевые площадки и форумы

### 6. Сохранение результатов

```bash
# Сохранить анализ
clients/[name]/seo/geo-audit-YYYY-MM-DD.md
```

Формат файла:
```markdown
# GEO-аудит: [Brand] ([domain])
Дата: YYYY-MM-DD

## GEO Visibility Index: XX/100

## Результаты по моделям
| Модель | Упоминаний | Из запросов | % |
|--------|-----------|-------------|---|

## Результаты по запросам
| Запрос | Claude | GPT-4o | Gemini | DeepSeek |
|--------|--------|--------|--------|----------|

## Конкуренты в ответах AI
| Конкурент | Упоминаний | В каких запросах |
|-----------|-----------|------------------|

## Рекомендации
### Приоритет 1 (срочно)
### Приоритет 2 (важно)
### Приоритет 3 (желательно)

## WebMCP Readiness (forward-looking)
| Критерий | Статус | Комментарий |
|----------|--------|-------------|
| Schema.org (Organization, Service, FAQ) | ✅/❌ | Базовый уровень AI-видимости |
| Structured Actions (потенциальные) | Список | Запись, заказ, звонок, расчёт — что может стать WebMCP endpoint |
| robots.txt AI-friendly | ✅/❌ | Не блокирует AI-краулеры (GPTBot, ClaudeBot, Google-Extended) |
| Машиночитаемый контент | ✅/❌ | HTML > JS-рендеринг, семантическая разметка |

> WebMCP (W3C, Google+Microsoft) — стандарт для AI-агентов. Chrome 145+ early preview.
> Сайты с WebMCP получат приоритет от AI-систем как сайты со Schema получают rich snippets.
> Подробнее: https://developer.chrome.com/blog/webmcp-epp
```

## Интерпретация результатов

| GEO Index | Оценка | Действие |
|-----------|--------|----------|
| 0-20 | Невидим | Срочно: контент + авторитет + Schema |
| 20-50 | Слабо виден | Усилить: больше контента, ссылки, отзывы |
| 50-80 | Хорошо | Поддерживать: регулярный контент |
| 80-100 | Отлично | Мониторить, защищать позиции |

## AI Crawlers Reference (14 ботов)

| Бот | Компания | Для чего |
|-----|----------|----------|
| GPTBot | OpenAI | Обучение + поиск ChatGPT |
| ChatGPT-User | OpenAI | Browse mode ChatGPT |
| ClaudeBot | Anthropic | Обучение Claude |
| PerplexityBot | Perplexity | AI-поиск |
| Googlebot-Extended | Google | AI Overviews / Gemini |
| Google-Extended | Google | Устаревшее имя (то же что выше) |
| CCBot | Common Crawl | Датасет для многих LLM |
| cohere-ai | Cohere | Обучение Command |
| Applebot-Extended | Apple | Apple Intelligence |
| Bytespider | ByteDance | TikTok AI |
| Amazonbot | Amazon | Alexa + AI |
| anthropic-ai | Anthropic | Альтернативное имя |
| FacebookBot | Meta | Meta AI |
| meta-externalagent | Meta | Meta AI agent |

## Зависимости

- Python 3.10+
- Библиотеки: `anthropic`, `openai`, `google-generativeai`
- API ключи в `/Users/antonk/artvision-data/tokens.json`:
  - `anthropic.api_key`
  - `openrouter.api_key`
  - `gemini.api_key`
  - `deepseek.api_key`
