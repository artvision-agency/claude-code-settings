---
name: commercial-factors-audit
description: Автоматический аудит сайта клиента по 100+ коммерческим факторам Яндекса с HTML-отчётом в стиле CAMEO
triggers:
  - коммерческие факторы
  - аудит коммерческий
  - комм факторы
  - коммерческий аудит
  - Artvision Pulse
  - presale аудит
  - quarterly review
---

# Commercial Factors Audit

Автоматизированная проверка сайта клиента по 118 коммерческим факторам Яндекса (источник: методичка Яндекса + наработки agency). Публичное название продукта: **artvision.pro Pulse**.

## Когда использовать

- **Presale-аудит** нового клиента — показать разрывы на старте
- **Quarterly review** действующего клиента — измерить динамику
- **Диагностика** перед запуском SEO/контекста — выявить утечки конверсии
- **Benchmark vs конкурент** — сравнить два сайта (запустить audit.py на оба)

## Когда НЕ использовать

- Одностраничные лендинги без каталога (25+ факторов e-commerce будут FAIL by design) — выбрать подмножество категорий вручную
- Закрытые разделы (ЛК, корпоративные) — требуют авторизации, помечаются как `manual`

## Workflow

```
URL клиента → audit.py → JSON → report.py → HTML
                                                  ↓
                    clients/{name}/audits/commercial-factors-YYYY-MM-DD.html
```

### Шаги

1. **Получить URL** сайта клиента (обычно из `clients/{name}/CLAUDE.md` → domain)
2. **Запустить audit** — краулит home + /contacts + /about + /delivery + /catalog (если доступны)
3. **Сгенерировать отчёт** — HTML в стиле CAMEO (эталон: `clients/kamey/presale/kp/cameo_kp.html`)
4. **Сохранить** в `clients/{name}/audits/commercial-factors-YYYY-MM-DD.html`
5. **Пропустить через factcheck** — `factcheck-v2.py` перед отправкой клиенту
6. **Деплой** — по стандартному workflow artvision.pro (если отчёт идёт в КП)

## Примеры запуска

### Базовый прогон

```bash
cd /Users/antonk/.claude/skills/commercial-factors-audit

# 1. Аудит
python3 scripts/audit.py https://tvorim-sovershenstvo.ru \
    --output=/tmp/tvorim-audit.json

# 2. Отчёт
python3 scripts/report.py /tmp/tvorim-audit.json \
    --output=/Users/antonk/artvision-data/clients/tvorim/audits/commercial-factors-$(date +%Y-%m-%d).html \
    --client-name="Творим Совершенство"
```

### Сравнение клиент vs конкурент

```bash
python3 scripts/audit.py https://client.ru --output=/tmp/client.json
python3 scripts/audit.py https://competitor.ru --output=/tmp/competitor.json
python3 scripts/report.py /tmp/client.json --compare=/tmp/competitor.json \
    --output=/tmp/versus.html --client-name="Client" --competitor-name="Competitor"
```

### Через Python (в скриптах / агентах)

```python
from scripts.audit import run_audit
from scripts.report import render_report

data = run_audit("https://example.com")
render_report(data, output_path="/tmp/report.html", client_name="Example")
```

## Интеграция с другими скиллами

| Скилл | Роль |
|-------|------|
| `seo-master` (Module 3 — Commercial Factors) | Запускает этот скилл как под-шаг, добавляет результаты в общий SEO-аудит |
| `presale-kp` | Использует `executive summary` (X/118, топ-5 критичных) как слайд «Разрывы» |
| `competitive-teardown` | Прогоняет этот скилл на 3-5 конкурентов → сравнительная таблица |
| `code-audit` / `factcheck-v2.py` | Обязательная проверка HTML-отчёта перед отправкой клиенту |

## Структура

```
commercial-factors-audit/
├── SKILL.md                   # этот файл
├── data/
│   └── factors-100.yaml       # 118 факторов (id, category, check_type, patterns, severity)
├── scripts/
│   ├── audit.py               # URL → crawl → check → JSON
│   └── report.py              # JSON → HTML (CAMEO-стиль)
└── templates/
    └── report.html.j2         # Jinja2 template
```

## Категории (7 блоков)

| ID | Категория | Факторов | Критичные |
|----|-----------|----------|-----------|
| 1  | Навигация и компания | 22 | Контакты, Телефон в шапке, Логотип |
| 2  | Доверие | 21 | Отзывы, Сертификаты, Яндекс Справочник |
| 3  | E-commerce | 19 | Доставка, Корзина, Гарантии |
| 4  | Customer engagement | 13 | Формы связи, Онлайн-чат, Мессенджеры |
| 5  | Content & SEO | 10 | HTTPS, Адаптивность, Meta title/description |
| 6  | Sales tools | 8 | УТП, Акции, Скидки |
| 7  | Product info | 25 | Фотографии, Цена, Рейтинг |

## Типы проверок (`check_type`)

| Тип | Описание | Инструмент |
|-----|----------|------------|
| `text_contains` | Поиск по тексту страницы | BeautifulSoup + нормализация |
| `url_exists` | Проверка наличия раздела по типовым URL | requests HEAD + парсинг меню |
| `element_exists` | CSS-селектор | BeautifulSoup select |
| `structured_data` | JSON-LD / микроразметка | json + BS4 |
| `http_status` | HTTPS / редиректы | requests |
| `metrika_counter` | Счётчик Метрики активен | Metrika API (auto-discovery) |
| `metrika_goals` | Цели конверсии настроены | Metrika API (auto-discovery) |
| `manual` | Требует человеческой проверки | TODO в отчёте |

## Auto-discovery токенов

Скрипт автоматически загружает `~/artvision-data/tokens.json` и определяет counter_id Метрики по домену. Не требует CLI-аргументов для токенов.

Если tokens.json не найден или нет подходящего counter_id -- API-проверки (`metrika_counter`, `metrika_goals`) корректно переключаются в `manual`-режим.

Поддерживаемые токены:
- `yandex.metrika.token` -- OAuth для API Метрики
- `yandex.metrika.*_counter` / `yandex.metrika.*_counters.*` -- автоопределение counter_id по домену

## Ограничения MVP (v0.1)

1. **Нет JS-рендеринга** — сайты на React/Vue с клиентской отрисовкой покажут часть FAIL не по делу. TODO: Playwright, но только когда будет диск.
2. **Нет авторизации** — ЛК, корпоративные кабинеты = `manual`
3. **Нет скриншотов** — только текстовые свидетельства (MVP решение, скриншоты через Playwright = следующая версия)
4. **robots.txt** — уважаем (audit.py делает проверку), но не парсим sitemap
5. **~30% факторов = `manual`** — репутация, отзовики, узнаваемость бренда, УТП, ЧПУ, размерный ряд и т.п. — требуют человека

## Бренд

- Отчёт подписан **artvision.pro** (строчные буквы, с `.pro`)
- Публичное название инструмента: **artvision.pro Pulse**
- Запрещено: "AI", "нейросеть", "ML" — см. `rules/security.md`
- Используем: "авторская методология", "экспертный анализ", "методика"

## Известные подводные камни

- **SPA без SSR** — requests получит пустой `<div id="app"></div>` → 80% FAIL. Проверить `view-source:` в браузере перед запуском
- **Региональные редиректы** — `https://domain.ru/msk/` → передавать в URL конкретный регион клиента
- **Таймаут 10с** — если сайт медленный, поднять через `--timeout=30`
- **Корзина на /korzina** — Яндекс не распознаёт, но пользователь может думать что «есть корзина»; скрипт проверит по URL-паттернам и пометит как FAIL с рекомендацией

## Roadmap

- [ ] v0.2 — Playwright для JS-сайтов (когда будет диск)
- [ ] v0.3 — Скриншоты ключевых блоков (header, корзина, контакты)
- [ ] v0.4 — Сравнение с 3-5 конкурентами в одном отчёте (сейчас — только 1 vs 1)
- [ ] v0.5 — Автопарсинг Яндекс.Справочника и Google Business по домену
- [ ] v1.0 — Интеграция в `/combine` — запуск на всех клиентах раз в квартал
