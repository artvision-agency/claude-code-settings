---
name: crag-research
description: >-
  Corrective RAG Research — исследование с обязательной перекрёстной проверкой.
  Каждое числовое утверждение проходит треугольник: 2+ источника, дата, тип метрики,
  confidence level. Применяет Corrective RAG + Agentic RAG + Self-RAG.
  Используй ВМЕСТО обычного research-analyst агента когда нужны точные числа.
  Triggers: 'crag', 'фактчек исследование', 'точные данные', 'проверенные данные',
  'corrective rag', 'исследование с проверкой', 'verified research',
  'market data factcheck', 'данные с источниками'
user-invocable: true
disable-model-invocation: false
allowed-tools: Read Write Edit Bash Grep Glob Agent WebSearch WebFetch
metadata:
  author: artvision
  version: "1.0"
  category: research
---

# CRAG Research — Corrective RAG Protocol

Исследование с **обязательной перекрёстной проверкой** каждого факта.
Применяется когда нужны **точные числа** для КП, дашбордов, отчётов клиентам.

## Принцип: Ни одного числа без треугольника

```
ЗАПРЕЩЕНО: WebSearch → первый результат → число в таблицу
ОБЯЗАТЕЛЬНО: WebSearch → 2+ источника → сравнить → confidence → число + метаданные
```

## Протокол (5 шагов)

### Шаг 1: Query Planning (НЕ ПРОПУСКАТЬ)

Перед поиском — определить:
1. **Какие факты нужны** — список конкретных утверждений для проверки
2. **Первоисточники** для каждого типа данных (см. Source Hierarchy)
3. **3+ запроса** на каждый факт — разными формулировками

```
Пример для "Telegram MAU в России":
  Query 1: site:statista.com telegram users Russia 2025
  Query 2: site:datareportal.com telegram russia monthly active
  Query 3: "mediascope" telegram россия MAU 2024 2025
  Query 4: telegram.org/blog russia users (официальный блог)
```

### Шаг 2: Source Hierarchy (приоритет источников)

| Tier | Тип источника | Примеры | Вес |
|:----:|---------------|---------|:---:|
| S | **Официальные отчёты** | SEC filings, IR presentations, пресс-релизы компаний | 1.0 |
| A | **Отраслевая аналитика** | Statista, Newzoo, Sensor Tower, data.ai, Mediascope | 0.9 |
| B | **Деловые СМИ** | Forbes, Bloomberg, RBC, Коммерсантъ | 0.7 |
| C | **Агрегаторы** | DemandSage, WorldPopulationReview, SimilarWeb | 0.5 |
| D | **Блоги / SEO-статьи** | "Top 10 statistics about..." | 0.3 |
| F | **Без источника** | Число без ссылки | 0.0 — НЕ ИСПОЛЬЗОВАТЬ |

**Правило:** Tier D и F — ТОЛЬКО как наводка для поиска первоисточника. Никогда как финальный источник.

### Шаг 3: Triangulation (перекрёстная проверка)

Для КАЖДОГО числа:

```
1. Найти число в источнике Tier S или A
2. Найти подтверждение в ДРУГОМ источнике (независимом)
3. Сравнить:
   → Расхождение ≤ 15% → CONFIRMED (взять среднее или более авторитетный)
   → Расхождение 15-40% → ESTIMATED (указать диапазон, оба источника)
   → Расхождение > 40% → CONFLICTING (указать оба числа, возможные причины)
   → Только 1 источник → UNCONFIRMED (указать единственный источник)
   → 0 источников → NOT FOUND (не включать в отчёт как факт)
```

### Шаг 4: Mandatory Metadata

Каждое число в отчёте ОБЯЗАНО иметь:

| Поле | Обязательно | Пример |
|------|:-----------:|--------|
| **Число** | ✅ | 80-90 млн |
| **Дата данных** | ✅ | Q4 2024 |
| **Тип метрики** | ✅ | MAU (monthly active users) |
| **Confidence** | ✅ | CONFIRMED / ESTIMATED / UNCONFIRMED / CONFLICTING |
| **Источник 1** | ✅ | Mediascope Q4 2024 |
| **Источник 2** | ⚠️ | Statista 2024 |
| **URL** | ⚠️ | statista.com/statistics/... |

Формат в тексте:
```
80-90 млн MAU [CONFIRMED, Q4 2024, Mediascope + Statista]
```

### Шаг 5: Self-Check (перед финализацией)

Перед выдачей результата — пройти чеклист:

- [ ] Каждое число имеет дату? (не "в 2020-х", а "Q4 2024")
- [ ] Каждое число имеет тип метрики? (MAU ≠ downloads ≠ registered)
- [ ] Каждое число имеет минимум 1 источник Tier A+?
- [ ] Числа внутренне непротиворечивы? (34.4M users ≠ 64% от 146M)
- [ ] Процент % — от какой базы? (население / интернет-пользователи / аудитория мессенджеров)
- [ ] Год данных совпадает между источниками?
- [ ] Нет смешения валют без указания? ($ ≠ ₽ ≠ €)

## Формат вывода

### Таблица с confidence

```markdown
| Факт | Значение | Confidence | Дата | Источник 1 | Источник 2 |
|------|----------|:----------:|------|------------|------------|
| TG MAU Россия | 80-90M | CONFIRMED | Q4 2024 | Mediascope | Statista |
| ARPU US mobile | $60.58 | CONFIRMED | 2025 | Statista | — |
| Геймеры Индия | 488-532M | ESTIMATED | 2024 | FICCI-EY: 488M | DemandSage: 532M |
```

### Сводка качества

В конце каждого отчёта:

```
## Data Quality Summary
- CONFIRMED: X утверждений (2+ источника, расхождение ≤15%)
- ESTIMATED: Y утверждений (источники расходятся 15-40%)
- UNCONFIRMED: Z утверждений (только 1 источник)
- CONFLICTING: W утверждений (расхождение >40%)
- NOT FOUND: N запросов без результата

Overall confidence: HIGH / MEDIUM / LOW
```

## Антипаттерны (ЗАПРЕЩЕНО)

| Антипаттерн | Пример | Почему плохо |
|-------------|--------|-------------|
| **Число без даты** | "560M геймеров в Индии" | Данные 2020 ≠ данные 2025 |
| **Смешение метрик** | "34.4M TG users, 64% penetration" | 34.4M/146M = 23%, не 64% |
| **Tier D как источник** | "по данным DemandSage..." | Агрегатор без первоисточника |
| **Красивое округление** | "ровно 100M пользователей" | Реальные числа не круглые |
| **Один запрос** | WebSearch → первый результат → готово | Нет triangulation |
| **Логическая несогласованность** | "население 20M, геймеров 25M" | Числа противоречат друг другу |

## Интеграция с другими скиллами

- **market-research** → вызывай `crag-research` для верификации числовых данных
- **presale-kp** → все числа в КП через CRAG протокол
- **cons** → данные конкурентов через CRAG

## Пример использования

```
User: crag "Telegram MAU по странам 2025, топ-5"

Agent flow:
1. Query planning: 4 запроса (site:statista, site:datareportal, telegram blog, businessofapps)
2. Fetch 4 источника → извлечь числа
3. Triangulate каждую страну:
   - India: Statista=100-120M, DataReportal=104M → CONFIRMED: 100-120M
   - Russia: Mediascope=85-90M, Statista=80M+ → CONFIRMED: 80-90M
4. Self-check: даты совпадают? метрики MAU? база %?
5. Output: таблица с confidence + quality summary
```
