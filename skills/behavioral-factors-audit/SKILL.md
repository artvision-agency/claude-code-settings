---
name: behavioral-factors-audit
description: Аудит сайта клиента по 32 поведенческим факторам Яндекса через Метрику, Вебмастер и PageSpeed. HTML-отчёт в стиле CAMEO.
triggers:
  - поведенческие факторы
  - поведенческий аудит
  - пф аудит
  - behavioral audit
  - Artvision Pulse Behavioral
  - аудит поведения
  - метрика аудит
  - core web vitals аудит
---

# Behavioral Factors Audit

Автоматическая проверка сайта по 32 поведенческим факторам Яндекса на основе данных Метрики, Вебмастера и PageSpeed Insights. Публичное название: **artvision.pro Pulse (Behavioral)**.

## Когда использовать

- **Presale с доступом к Метрике** — клиент дал логин или передал counter_id (гостевой доступ)
- **Quarterly review** действующего клиента — сверить ПФ динамику после SEO/CRO
- **Диагностика утечек** — низкая конверсия при хороших позициях = проблема в ПФ
- **Core Web Vitals перед релизом** — обязательный прогон перед запуском нового дизайна
- **Комплиментарный аудит к `commercial-factors-audit`** — коммерческий показывает каркас, этот — фактическое поведение

## Когда НЕ использовать

- Нет ни Метрики, ни Вебмастера, ни желания ждать PageSpeed (~20 сек на URL) — возьми `commercial-factors-audit`
- Сайт только запустился (< 2 недель данных) — Метрика даст статистический шум

## Workflow

```
URL клиента [+ counter_id] → audit.py → JSON → report.py → HTML
                                                              ↓
                clients/{name}/audits/behavioral-factors-YYYY-MM-DD.html
```

### Шаги

1. **Получить URL + counter_id** — `clients/{name}/CLAUDE.md` → поля `domain` + `metrika_counter_id`
2. **Проверить токены** — `tokens.json` → `yandex.metrika.token`, `yandex.webmaster.token`
3. **Запустить audit** — вызов трёх API параллельно, сбор сырых данных + маппинг в FactorResult
4. **Сгенерировать отчёт** — HTML в стиле CAMEO + графики (device split, источники)
5. **Сохранить** в `clients/{name}/audits/behavioral-factors-YYYY-MM-DD.html`
6. **Пропустить через factcheck** — `factcheck-v2.py` перед отправкой клиенту

## Примеры запуска

### С полным доступом (Метрика + Вебмастер + PageSpeed)

```bash
cd /Users/antonk/.claude/skills/behavioral-factors-audit
source venv/bin/activate

# 1. Аудит — 30 дней, счётчик Метрики клиента
python3 scripts/audit.py https://tvorim-sovershenstvo.ru \
    --counter-id=12345678 \
    --days=30 \
    --output=/tmp/tvorim-behavioral.json

# 2. Отчёт
python3 scripts/report.py /tmp/tvorim-behavioral.json \
    --output=/Users/antonk/artvision-data/clients/tvorim/audits/behavioral-factors-$(date +%Y-%m-%d).html \
    --client-name="Творим Совершенство"
```

### Degraded stub (только URL, без Метрики)

```bash
# Работает: PageSpeed (без ключа) + HTML-check + manual-факторы
# Не работает (status: na): все метрики Метрики + Вебмастера
python3 scripts/audit.py https://new-client.ru \
    --output=/tmp/stub-audit.json

python3 scripts/report.py /tmp/stub-audit.json \
    --output=/tmp/stub-report.html \
    --client-name="Новый клиент"
```

### Через Python (в pipeline / агентах)

```python
from scripts.audit import run_audit
from scripts.report import render_report

data = run_audit(
    target_url="https://example.com",
    counter_id=12345678,
    period_days=30,
)
render_report(data, output_path="/tmp/report.html", client_name="Example")
```

## Настройка доступа

### Яндекс.Метрика (обязательно для 60% факторов)

1. **Получить OAuth токен:** https://oauth.yandex.ru → приложение с правами Метрики (`metrika:read`)
2. **Сохранить в `tokens.json`:**
   ```json
   "yandex": {
     "metrika": {
       "token": "y0_AgAAAA...",
       "client_id": "...",
       "client_secret": "..."
     }
   }
   ```
3. **Получить counter_id:** metrika.yandex.ru → счётчик клиента → ID в URL
4. **Права:** гостевой доступ «Только просмотр» достаточно

### Яндекс.Вебмастер (для SERP-факторов: CTR, позиции)

1. **OAuth токен** с правами `webmaster:verify` + `webmaster:hostinfo`
2. **user_id** — возвращается из GET `/v4/user`
3. Домен должен быть **подтверждён** в Вебмастере клиента
4. **Сохранить в `tokens.json`:**
   ```json
   "yandex": {
     "webmaster": {
       "token": "y0_AgAAAA...",
       "user_id": "1234567"
     }
   }
   ```

### Google PageSpeed Insights (опционально)

- Работает **без ключа** до 25K запросов/день на IP
- Для стабильности — получить ключ: https://console.cloud.google.com → APIs → PageSpeed Insights API
- Добавить в `tokens.json`:
  ```json
  "google": {
    "pagespeed": {"key": "AIza..."}
  }
  ```

## Интеграция с другими скиллами

| Скилл | Роль |
|-------|------|
| `commercial-factors-audit` | Парный скилл: коммерческие факторы (структура), этот — поведенческие (факт) |
| `seo-master` | Module 4 (PF) — запускает этот скилл как под-шаг |
| `presale-kp` | Использует executive summary (score, топ-5 разрывов) + графики (device split) |
| `cro` | Получает список fail-факторов как бэклог тестов |
| `code-audit` / `factcheck-v2.py` | Обязательная проверка HTML-отчёта перед отправкой |

## Структура

```
behavioral-factors-audit/
├── SKILL.md                   # этот файл
├── data/
│   └── factors.yaml           # 32 фактора (id, category, check_type, thresholds, severity)
├── scripts/
│   ├── audit.py               # API calls → JSON
│   └── report.py              # JSON → HTML (CAMEO-стиль)
├── templates/
│   └── report.html.j2         # Jinja2 template
└── venv/                      # Python 3.11+ окружение
```

## Категории (6 блоков)

| ID | Категория | Факторов | Критичные | Источник данных |
|----|-----------|----------|-----------|------------------|
| 1  | Engagement (вовлечённость) | 5 | Время, глубина, отказы, 15-сек правило | Метрика |
| 2  | SERP behavior | 4 | CTR, позиции, no-click, dwell time | Вебмастер + Метрика |
| 3  | Interaction | 6 | Клики, формы, скролл, клик-карта, Вебвизор | Метрика (целевые события) |
| 4  | Segmentation | 6 | Mobile/Desktop, источники, гео | Метрика (сегменты) |
| 5  | Conversions | 3 | Настройка целей, CR, CR по источникам | Метрика (цели) |
| 6  | Technical | 8 | LCP, CLS, INP, TTFB, Perf Score, 404, JS-errors | PageSpeed + Метрика |

## Типы проверок (`check_type`)

| Тип | Описание | Инструмент |
|-----|----------|------------|
| `metrika_api` | Метрика Stat API v1 | OAuth + `api-metrika.yandex.net/stat/v1/data` |
| `webmaster_api` | Вебмастер API v4 | OAuth + `api.webmaster.yandex.net/v4` |
| `pagespeed_api` | PageSpeed v5 (Lighthouse) | `googleapis.com/pagespeedonline/v5/runPagespeed` |
| `html_check` | Парсинг HTML главной | requests + BeautifulSoup |
| `manual` | Требует человеческой проверки | TODO в отчёте |

## Graceful degradation

| Что отсутствует | Что произойдёт |
|------------------|-----------------|
| `counter_id` не указан | 17 факторов → `status: na`, в evidence: «Не передан counter_id» |
| `yandex.metrika.token` отсутствует | То же — 17 факторов в NA |
| `yandex.webmaster.token` отсутствует | 4 SERP-фактора → NA |
| Домен не подтверждён в Вебмастере | SERP-факторы → NA с пометкой |
| Нет `google.pagespeed.key` | Всё равно работает (25K/день лимит по IP) |
| Сайт недоступен для PageSpeed | 6 CWV-факторов → NA |

Отчёт **всегда** рендерится — даже если все API молчат: останутся `manual` факторы как чеклист для клиента + HTML-проверки.

## Пороги по умолчанию

| Метрика | PASS | WARN | FAIL |
|---------|------|------|------|
| Среднее время на сайте | ≥120 сек | 60-120 сек | <60 сек |
| Глубина | ≥2.5 | 1.8-2.5 | <1.8 |
| Отказы (bounce) | ≤15% | 15-30% | >30% |
| Мобильные отказы | ≤20% | 20-40% | >40% |
| CTR в SERP | ≥4% | 2-4% | <2% |
| LCP | ≤2.5с | 2.5-4.0с | >4.0с |
| CLS | ≤0.1 | 0.1-0.25 | >0.25 |
| INP | ≤200мс | 200-500мс | >500мс |
| Performance Score (mobile) | ≥80 | 50-80 | <50 |
| Доля 404 | ≤1% | 1-3% | >3% |
| Конверсия в цель | ≥2% | 0.8-2% | <0.8% |

## Бренд

- Подпись отчёта — **artvision.pro** (строчные буквы, с `.pro`)
- Продукт — **artvision.pro Pulse (Behavioral)**
- Запрещено: «AI», «нейросеть», «ML» (см. `rules/security.md`)
- Используем: «авторская методология», «аналитический движок», «экспертные пороги»

## Известные подводные камни

- **Метрика латентность:** данные за сегодня доступны с задержкой 1-2 часа. Период по умолчанию — 30 дней (вчера - 31 день)
- **Webmaster API rate limit:** 100 req/min. Скрипт делает 1 запрос на домен → запас большой
- **PageSpeed 25K/день на IP:** при массовом прогоне (>100 URL) — использовать ключ
- **SPA без SSR:** Метрика считает его как одну страницу = искусственно низкий pageDepth. Проверить настройку «SPA / History API» в счётчике
- **Гостевой доступ в Метрику** — иногда у клиента «Редактор», и нам дают только «Просмотр». Оба варианта работают для read-only API
- **Таймаут PageSpeed:** на медленных сайтах — 60+ сек. Скрипт поднимает timeout до 60 для PageSpeed
- **Домен с www/без www** — в Вебмастере один вариант подтверждён, другой — нет. Проверить через `GET /v4/user/{uid}/hosts`

## Roadmap

- [ ] v0.2 — парсинг JS-ошибок из Метрики API (сейчас `manual`)
- [ ] v0.3 — Adblock детект через собственный JS (сейчас `manual`)
- [ ] v0.4 — сравнение период vs период (неделя vs предыдущая) с динамикой
- [ ] v0.5 — сравнение с бенчмарками ниши (берём медиану по 10 конкурентам клиента)
- [ ] v0.6 — тепловая карта фактор × сегмент (mobile/desktop × engagement)
- [ ] v1.0 — `/combine` интеграция: ежемесячный авто-прогон всех активных клиентов
