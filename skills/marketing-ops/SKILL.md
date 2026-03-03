---
name: marketing-ops
description: "Multi-agent маркетинговые операции: SEO/PPC/SERM. Dispatcher + Fan-Out агенты. Режимы: audit (полный аудит), monitor (мониторинг), optimize (оптимизация), report (отчёт). Триггеры: 'маркетинг аудит', 'SEO команда', 'PPC оптимизация', 'SERM мониторинг', 'marketing ops', 'агентная команда'."
argument-hint: "<mode> <client> [focus]  — mode: audit|monitor|optimize|report, client: алиас клиента, focus: seo|ppc|serm|all"
---

# /marketing-ops — Multi-Agent Marketing Operations

## Что это

Оркестратор маркетинговых агентов. Запускает параллельные команды SEO/PPC/SERM агентов,
собирает результаты, формирует отчёт с рекомендациями.

Фреймворк: `processes/agent-marketing-framework.md`

## Архитектура

```
┌──────────────────────────────────────────────────────┐
│              ORCHESTRATOR (этот скилл)                │
│  Парсит команду → выбирает режим → роутит агентам    │
│  Собирает результаты → верифицирует → отчёт          │
└────────┬──────────────┬──────────────────┬────────────┘
         │              │                  │
   ┌─────▼─────┐  ┌────▼─────┐   ┌───────▼───────┐
   │ SEO Team  │  │ PPC Team │   │  SERM Team    │
   │ 4 агента  │  │ 3 агента │   │  3 агента     │
   └───────────┘  └──────────┘   └───────────────┘
```

## Режимы работы

### 1. `audit` — Полный маркетинговый аудит

```
/marketing-ops audit geely seo
/marketing-ops audit artvision all
```

**Что делает:**
- SEO: keyword research + технический аудит + content gaps + конкуренты
- PPC: анализ кампаний + эффективность ставок + quality score
- SERM: SERP по бренду + отзывы + sentiment
- Всё параллельно, затем верификация + отчёт

### 2. `monitor` — Мониторинг (для cron/регулярного запуска)

```
/marketing-ops monitor geely seo
/marketing-ops monitor otido serm
```

**Что делает:**
- SEO: проверка позиций, алерты при падении >5 позиций
- PPC: проверка CPA/ROAS, алерты при аномалиях
- SERM: новые отзывы, негатив, изменения в SERP по бренду

### 3. `optimize` — Оптимизация по данным

```
/marketing-ops optimize ant-partners seo
```

**Что делает:**
- Берёт данные из последнего аудита/мониторинга
- SEO: оптимизация title/description, content recommendations
- PPC: рекомендации по ставкам и объявлениям
- SERM: план вытеснения негатива, черновики ответов

### 4. `report` — Отчёт клиенту

```
/marketing-ops report geely all
```

**Что делает:**
- Собирает все данные по клиенту за период
- Формирует отчёт в формате `clients/[name]/reports/`
- KPI + динамика + рекомендации

---

## Парсинг аргументов

```
Вход: /marketing-ops <mode> <client> [focus]

mode:   audit | monitor | optimize | report
client: алиас клиента (из CLAUDE.md)
focus:  seo | ppc | serm | all (default: all)
```

Если аргументы неполные — спросить через AskUserQuestion.

---

## Алгоритм выполнения

### Шаг 0: Подготовка

1. Определить клиента по алиасу → найти папку `clients/[name]/`
2. Прочитать `config.yaml` клиента (если есть) — домен, запросы, бренд
3. Определить доступные данные: GSC, Topvisor, рекламные кабинеты

### Шаг 1: Запуск агентов (Parallel Fan-Out)

В зависимости от mode + focus, запустить агентов ПАРАЛЛЕЛЬНО:

#### SEO Agents (focus=seo или all)

```
# Агент 1: Deep Research
Task(
  subagent_type="research-analyst",
  description="SEO keyword research",
  prompt="Ты SEO-аналитик. Клиент: {client}, домен: {domain}.

ЗАДАЧИ:
1. WebSearch по основным запросам клиента — кто в топ-5 Яндекса
2. Найти 10-20 ключевых запросов для домена (коммерческие + инфо)
3. Для каждого запроса: примерная частотность, интент, текущая позиция (если известно)
4. Content gaps: темы у конкурентов, которых нет у клиента
5. Кластеризовать по группам

ФОРМАТ ВЫВОДА: JSON
{
  'keywords': [...],
  'competitors': [...],
  'content_gaps': [...],
  'clusters': [...]
}

ВАЖНО: Данные ЯНДЕКС в приоритете. Google = fallback с пометкой.",
  run_in_background=true
)

# Агент 2: Technical SEO
Task(
  subagent_type="seo-analyzer",
  description="Technical SEO audit",
  prompt="Ты технический SEO-специалист. Аудит сайта: {domain}

ЗАДАЧИ:
1. Проверь robots.txt: curl -sL {domain}/robots.txt
2. Проверь sitemap: curl -sL {domain}/sitemap.xml | head -50
3. Мета-теги 5 главных страниц: curl -sL URL | grep -E '<title|<meta name=\"description\"'
4. Schema markup: curl -sL URL | grep -oE 'application/ld\\+json'
5. HTTPS, канонические URL, редиректы

ФОРМАТ: JSON с приоритетами (critical/high/medium/low)

ПОМНИ: WebFetch ТЕРЯЕТ <head>! Только curl для мета-тегов.",
  run_in_background=true
)

# Агент 3: Content Analysis
Task(
  subagent_type="seo-specialist",
  description="Content optimization analysis",
  prompt="Ты контент-оптимизатор. Анализ контента: {domain}

ЗАДАЧИ:
1. WebFetch главной + 3 ключевых страницы — оцени качество контента
2. Наличие H1, H2 структуры, внутренней перелинковки
3. Сравни с топ-3 конкурентами из SERP по главному запросу
4. Рекомендации: что добавить, что улучшить, какие страницы создать

ФОРМАТ: Список рекомендаций с приоритетами",
  run_in_background=true
)
```

#### SERM Agents (focus=serm или all)

```
# Агент 4: Brand Monitoring
Task(
  subagent_type="research-analyst",
  description="SERM brand monitoring",
  prompt="Ты SERM-аналитик. Мониторинг бренда: {brand}

ЗАДАЧИ:
1. WebSearch '{brand} отзывы' — кто в топ-10
2. WebSearch '{brand} отзывы сотрудников' — если релевантно
3. WebSearch '{brand} {город} отзывы' — локальный SERP
4. Для каждого результата: URL, тональность (pos/neg/neutral), контролируем или нет
5. Общий sentiment score

ФОРМАТ: JSON
{
  'serp_brand': [...],
  'serp_reviews': [...],
  'sentiment_score': 0-100,
  'controlled_positions': N,
  'negative_positions': [...]
}",
  run_in_background=true
)
```

#### PPC Agents (focus=ppc или all)

```
# Агент 5: PPC Analysis (если есть рекламные кабинеты)
Task(
  subagent_type="data-analyst",
  description="PPC campaign analysis",
  prompt="Ты PPC-аналитик. Анализ рекламных кампаний клиента: {client}

ЗАДАЧИ:
1. Проверить наличие рекламы по бренд-запросам: WebSearch '{brand}'
2. Проверить конкурентов в рекламе: кто размещается по нашим запросам
3. Рекомендации по структуре кампаний на основе keyword research
4. Оценка конкурентности ниши в контексте

ФОРМАТ: Рекомендации с приоритетами",
  run_in_background=true
)
```

### Шаг 2: Сбор результатов

После завершения ВСЕХ агентов:
1. Прочитать output каждого агента
2. Дедупликация (агенты могут найти одно и то же)
3. Группировка по приоритетам

### Шаг 3: Верификация (ОБЯЗАТЕЛЬНО!)

```
Task(
  subagent_type="competitive-analyst",
  description="Verify agent findings",
  prompt="Ты ревизор данных. Проверь результаты агентов на достоверность.

ДАННЫЕ ДЛЯ ПРОВЕРКИ:
{agent_results_summary}

ЗАДАЧИ:
1. Перекрёстная проверка ключевых фактов (позиции, конкуренты)
2. Отметь неподтверждённые данные как 'заявлено' / 'требует проверки'
3. Исправь явные ошибки

ФОРМАТ: Исправленная версия данных + список сомнительных фактов"
)
```

### Шаг 4: Формирование отчёта

На основе верифицированных данных:

```
# Маркетинговый аудит: {client}
Дата: {date}

## Резюме
- SEO: оценка X/10, N критичных проблем
- PPC: [статус]
- SERM: sentiment {score}%, контролируем {N}/{total} позиций

## SEO
### Keyword Research
[из Research Agent]

### Технические проблемы
[из Technical Agent, с приоритетами]

### Контент
[из Content Agent]

## SERM
### SERP по бренду
[из Monitoring Agent]

### Рекомендации
[конкретные действия]

## PPC
[из PPC Agent]

## План действий (приоритет)
1. [Критичное]
2. [Важное]
3. [Желательное]
```

Сохранить в: `clients/{name}/reports/marketing-ops_{date}.md`

### Шаг 5: Задачи в Asana

Для каждой рекомендации с приоритетом critical/high:
- Создать задачу в Asana через MCP (asana_create_task)
- Назначить секцию: Тех.SEO / Контент / План

---

## HITL (Human-in-the-Loop) — где СТОП

| Действие | Авто? | Почему |
|----------|-------|--------|
| Аудит / мониторинг | Авто | Данные в файл, не публикация |
| Рекомендации | Авто | Черновик в репо |
| Задачи Asana | Авто | Внутренняя система |
| Публикация контента | **СТОП** | Публичное |
| Ответ на отзыв | **СТОП** | Публичное |
| Изменение ставок PPC | **СТОП** | Деньги |
| Отчёт клиенту | **СТОП** | Клиентская коммуникация |

---

## Маппинг агентов

| Роль | subagent_type | Когда |
|------|---------------|-------|
| Keyword Research | `research-analyst` | audit, optimize |
| Technical SEO | `seo-analyzer` | audit, monitor |
| Content Analysis | `seo-specialist` | audit, optimize |
| Brand Monitoring | `research-analyst` | monitor, audit |
| SERP Displacement | `seo-specialist` | optimize |
| PPC Analysis | `data-analyst` | audit, optimize |
| Response Drafts | `content-marketer` | optimize |
| Verification | `competitive-analyst` | ВСЕГДА |
| Reporting | `data-analyst` | report |

---

## Cron-режим (24/7 мониторинг)

Для автоматического мониторинга нужен cron или LaunchAgent:

```bash
# Каждые 6 часов — SERM мониторинг критичных клиентов
0 */6 * * * cd ~/artvision-data && claude --print "/marketing-ops monitor geely serm"

# Раз в неделю — SEO мониторинг всех клиентов
0 8 * * 1 cd ~/artvision-data && claude --print "/marketing-ops monitor all seo"

# 1-го числа — месячный отчёт
0 10 1 * * cd ~/artvision-data && claude --print "/marketing-ops report all all"
```

**ВАЖНО:** Требует VDS/VPS с Claude Code для 24/7 работы.

---

## Примеры использования

```
/marketing-ops audit geely all          # Полный аудит Geely
/marketing-ops audit artvision seo      # SEO-аудит artvision.pro
/marketing-ops monitor otido serm       # SERM мониторинг OTIDO
/marketing-ops optimize ant-partners seo # Оптимизация ANT Partners
/marketing-ops report madwave all       # Отчёт Madwave за период
```

---

## Сервисы и доступы: Яндекс + Google

### Яндекс (ПРИОРИТЕТ для RU-рынка)

| Сервис | Что даёт | Доступ | Использование |
|--------|----------|--------|---------------|
| **Яндекс.Вебмастер** | Индексация, ошибки, позиции, sitemap | Логин клиента / делегирование | Technical SEO Agent, Monitor |
| **Яндекс.Метрика** | Трафик, конверсии, вебвизор, карты | Гостевой доступ / API-ключ | Analytics Agent, Report |
| **Яндекс.Директ** | PPC кампании, ставки, объявления | Доступ к кабинету | PPC Team (ВСЕ операции с бюджетом = HITL!) |
| **Яндекс.Карты** | Отзывы, рейтинг, карточка организации | Яндекс.Бизнес кабинет | SERM Monitor |
| **Яндекс.Wordstat** | Частотность запросов | Открытый (парсинг) | Research Agent |
| **Topvisor** | Позиции Яндекс/Google, API | `tokens.json` → topvisor_api_key | Rank Tracking Agent (ПЛАТНЫЙ — HITL!) |

### Google

| Сервис | Что даёт | Доступ | Использование |
|--------|----------|--------|---------------|
| **Google Search Console** | Индексация, CTR, позиции, запросы | Верификация домена / делегирование | Technical SEO Agent, Monitor |
| **Google Analytics 4** | Трафик, конверсии, аудитории | Доступ к свойству | Analytics Agent, Report |
| **Google Ads** | PPC кампании, ставки, Quality Score | Доступ к аккаунту / MCC | PPC Team (бюджет = HITL!) |
| **Google Maps / Бизнес** | Отзывы, карточка, локальное SEO | Google Business Profile | SERM Monitor |
| **PageSpeed Insights** | Core Web Vitals, скорость | Открытый API | Technical SEO Agent |

### Доступы — что нужно от клиента

При онбординге клиента (`/new-client`) запрашивать ВСЁ сразу:

```
ОБЯЗАТЕЛЬНЫЕ ДОСТУПЫ (записать в clients/[name]/access.md):

Яндекс:
□ Яндекс.Вебмастер — гостевой доступ или делегирование на adw.artvision.pro@gmail.com
□ Яндекс.Метрика — гостевой доступ (чтение) на adw.artvision.pro@gmail.com
□ Яндекс.Директ — доступ к кабинету (если есть PPC)
□ Яндекс.Бизнес — доступ к карточке (если есть SERM)

Google:
□ Google Search Console — подтвердить домен + дать доступ adw.artvision.pro@gmail.com
□ Google Analytics 4 — доступ на чтение adw.artvision.pro@gmail.com
□ Google Ads — доступ к аккаунту (если есть PPC)
□ Google Business Profile — менеджер (если есть SERM)

CMS:
□ Админка сайта — логин/пароль или роль
□ FTP/SSH — если нужен прямой доступ к файлам

Дополнительно:
□ Логин/пароль от хостинга (если нужен SSL, htaccess)
□ DNS-доступ (если нужен для GSC верификации)
```

### API-ключи в tokens.json

```json
{
  "topvisor_api_key": "...",       // Позиции Яндекс/Google
  "yandex_metrika_token": "...",   // Яндекс.Метрика API
  "google_search_console": "...",  // GSC API (service account)
  "google_analytics": "...",       // GA4 API
  "yandex_direct_token": "...",    // Яндекс.Директ API
  "google_ads_developer_token": "..." // Google Ads API
}
```

**ПРАВИЛО:** Все API-ключи → `tokens.json`. Коммит tokens.json = ТОЛЬКО после подтверждения.

### Приоритет данных

```
SERP-анализ:     Яндекс ПЕРВЫЙ → Google как дополнение
Позиции:         Topvisor (оба) → GSC (только Google)
Трафик:          Яндекс.Метрика → GA4
PPC:             Яндекс.Директ → Google Ads
Отзывы:          Яндекс.Карты + Google Maps + отзовики
Технический SEO: curl + hybrid-seo-audit.py (универсальный)
```

---

## Зависимости

- `scripts/hybrid-seo-audit.py` — для технического SEO
- `scripts/asana_cli.py` — для создания задач
- MCP Asana — для прямого создания задач
- `processes/agent-marketing-framework.md` — полный фреймворк
- `config.yaml` клиентов — домены, запросы, бренды
- `tokens.json` — API-ключи Topvisor, Яндекс, Google
- `clients/[name]/access.md` — доступы конкретного клиента

---

## Ошибки и уроки

| Ошибка | Урок |
|--------|------|
| Данные без верификации | ВСЕГДА запускать competitive-analyst |
| WebFetch для мета-тегов | Только curl -sL \| grep |
| SERP Google вместо Яндекс | Яндекс = приоритет для RU |
| Агенты коммитят независимо | Коммит ПОСЛЕ всех агентов |
| Нет config.yaml клиента | Спросить домен + запросы перед стартом |
