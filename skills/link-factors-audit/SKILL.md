---
name: link-factors-audit
description: Авторский аудит ссылочного профиля сайта по 27 параметрам Яндекса — HTML-отчёт в стиле CAMEO с графиками динамики
triggers:
  - ссылочный аудит
  - ссылочные факторы
  - линк аудит
  - link audit
  - бэклинки
  - backlinks
  - анкор-лист
  - ссылочный профиль
  - Artvision LinkForge
  - минусинск
---

# Link Factors Audit

Автоматизированный аудит **ссылочного профиля** сайта по 27 факторам ранжирования Яндекса (внешние + внутренние ссылки). Публичное название продукта: **artvision.pro LinkForge** (авторская методология).

## Когда использовать

- **Presale** — показать клиенту ссылочный разрыв vs 3-5 конкурентов
- **Risk audit** — перед стартом SEO, проверить риски Минусинска (спайки, переспам анкоров, токсичные доноры)
- **Quarterly review** — измерить динамику ссылочной массы (прирост/потери)
- **Линкбилдинг planning** — найти ключевых доноров конкурентов, которых нет у клиента
- **Фактчек канонических ссылок** — перед правкой технички

## Когда НЕ использовать

- Сайт <6 месяцев с нулевой массой — проверять нечего, сразу к линкбилдинг-плану (skill `linkbuilding`)
- Мультирегиональные монстры (Wildberries, Ozon) — масштаб не ловится API за разумные деньги

## Workflow

```
Домен клиента → audit.py → JSON → report.py → HTML
                   ↓                              ↓
           API: Checktrust/Serpstat/Ahrefs   clients/{name}/audits/
           + парсинг SERP                     link-audit-YYYY-MM-DD.html
```

### Шаги

1. **Проверить API** — `python3 -c "import json; print([k for k in json.load(open('tokens.json')).keys() if k in ('checktrust','serpstat','ahrefs','majestic')])"`
2. **Получить домен** из `clients/{name}/CLAUDE.md`
3. **Запустить аудит** — собирает данные по ВСЕМ 27 факторам (с заглушками если нет API)
4. **Сгенерировать отчёт** — HTML в стиле CAMEO + графики matplotlib (embedded PNG)
5. **Factcheck** — `factcheck-v2.py` перед отправкой клиенту
6. **Сохранить** в `clients/{name}/audits/link-audit-YYYY-MM-DD.html`

## Примеры запуска

### Базовый прогон

```bash
cd /Users/antonk/.claude/skills/link-factors-audit

# venv при первом запуске
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. Аудит
python3 scripts/audit.py tvorim-sovershenstvo.ru \
    --output=/tmp/tvorim-link.json \
    --competitors=dental-msk.ru,denta-clinic.ru

# 2. Отчёт
python3 scripts/report.py /tmp/tvorim-link.json \
    --output=/Users/antonk/artvision-data/clients/tvorim/audits/link-audit-$(date +%Y-%m-%d).html \
    --client-name="Творим Совершенство"
```

### Программный вызов

```python
from scripts.audit import run_audit
from scripts.report import render_report

data = run_audit("example.com", competitors=["compa.ru", "compb.ru"])
render_report(data, output_path="/tmp/link.html", client_name="Example")
```

## 27 факторов (5 групп)

| Группа | Факторов | Ключевые |
|--------|----------|----------|
| 1. Внешний ссылочный профиль | 12 | Backlinks, ref domains, DR/DA, TLD, homepage vs inner |
| 2. Анкор-лист и токсичность | 5 | Anchor distribution, переспам, toxic donors, brand mentions |
| 3. Динамика и возраст | 3 | Link velocity 12мес, lost links, median age |
| 4. Внутренняя перелинковка | 5 | Orphans, click depth, broken internal, hreflang, redirects |
| 5. Конкурентный разрыв | 2 | Backlink gap, competitor unique donors |

Полный список — `data/factors.yaml`.

## API и источники

**Порядок fallback:**
1. **Checktrust API** — основной (бесплатный quota 100/сутки), токсичность и DR
2. **Serpstat API** — backlinks + конкуренты
3. **Ahrefs API** — premium, если есть ключ
4. **Majestic** — trust flow / citation flow
5. **Fallback** — парсинг SERP + Yandex Webmaster (при наличии creds)

**Проверка токенов (автоматическая):**
```bash
cd /Users/antonk/.claude/skills/link-factors-audit
python3 -c "import sys; sys.path.insert(0,'scripts'); from providers import available_providers; [print(f'  {k}: {\"OK\" if v else \"missing\"}') for k,v in available_providers().items()]"
```

Токены загружаются автоматически из `~/artvision-data/tokens.json` (вложенная структура):
- `yandex.webmaster.token` + `yandex.webmaster.user_id` -- внешние ссылки Яндекса
- `topvisor.api_key` + `topvisor.user_id` -- позиции, проекты
- `checktrust` (top-level) -- XT/XS, токсичность
- `serpstat` (top-level) -- backlinks, конкуренты
- `ahrefs` (top-level) -- premium backlinks

Если API не настроены, фактор помечается `manual` + рекомендация добавить токен.
Yandex.Webmaster используется как fallback для факторов 1,2,6,8,10,19,20 когда Serpstat/Ahrefs недоступны.

## Структура

```
link-factors-audit/
├── SKILL.md
├── requirements.txt
├── data/
│   └── factors.yaml           # 27 факторов
├── scripts/
│   ├── audit.py               # домен + API → JSON
│   ├── report.py              # JSON → HTML + графики
│   └── providers.py           # обёртки над API (Checktrust/Serpstat/Ahrefs/Majestic)
└── templates/
    └── report.html.j2         # Jinja2, CAMEO-стиль + embed PNG
```

## Интеграция

| Скилл | Роль |
|-------|------|
| `seo-master` (Module 4 — Link profile) | Запускает этот скилл как под-шаг общего SEO-аудита |
| `presale-kp` | Раздел "Ссылочный разрыв" в КП — top-5 донаров конкурентов |
| `linkbuilding` | Принимает на вход список недостающих доноров для аутрича |
| `competitive-teardown` | Прогоняет skill на 3-5 конкурентов, делает сравнительную таблицу |

## Бренд

- Отчёт подписан **artvision.pro**
- Публичное название инструмента: **artvision.pro LinkForge**
- Запрещено: "AI", "нейросеть", "ML" → используем "авторская методология", "экспертный анализ"

## Ограничения MVP (v0.1)

1. **Без Ahrefs/Serpstat premium** — в fallback-режиме 60% факторов = `manual`
2. **SERP-парсинг хрупок** — антибот Яндекса рубит >10 запросов/мин → retry с паузами
3. **Графики matplotlib** — встраиваются в HTML как base64 PNG (не SVG), чтобы работало при пересылке файлом
4. **Нет глубокого контент-анализа донаров** — только метаданные, без анализа тематики текста

## Подводные камни

- **Checktrust** — даёт XT (X-Trust) и X-Spam, но без истории; для спайков нужен Ahrefs/Serpstat
- **Yandex.Webmaster** — показывает только *свои* ссылки, конкурентов не увидишь
- **TLD-распределение** — `.рф` домены нужно декодировать punycode (`xn--p1ai`)
- **Переспам анкоров** — считается как % exact match от всех анкоров, но не учитывает синонимы — это нормально для MVP

## Roadmap

- [x] v0.2 — интеграция Yandex Webmaster API (external links summary/samples/history) + auto token discovery
- [ ] v0.3 — sunburst-диаграмма TLD + DR (Plotly)
- [ ] v0.4 — авторские скрипты детекции PBN (N-gram хостингов, whois patterns)
- [ ] v1.0 — сводный dashboard по всем клиентам раз в квартал через `/combine`
