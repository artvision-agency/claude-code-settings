---
name: seo-factors-audit
description: Сквозной SEO-аудит — оркестратор 4 модулей (коммерч / тексто / ссылоч / поведенч) → сводный dashboard в стиле CAMEO
triggers:
  - полный seo аудит
  - sqo аудит
  - seo факторы
  - сквозной аудит
  - seo дашборд
  - artvision pulse full
  - комплексный seo
---

# SEO Factors Audit — Оркестратор

Единый управляющий скилл, собирающий результаты 4 модулей аудита в один executive dashboard в стиле CAMEO. Публичное название: **artvision.pro Pulse (Full)**.

## Архитектура

```
seo-factors-audit (orchestrator)
├── commercial-factors-audit  ← коммерческие факторы (118 факторов)
├── text-factors-audit        ← текстовые факторы
├── link-factors-audit        ← ссылочные факторы
└── behavioral-factors-audit  ← поведенческие факторы
```

Каждый модуль работает независимо и выдаёт **стандартизированный JSON + HTML**. Оркестратор:
1. Запускает 4 модуля (последовательно или параллельно)
2. Читает 4 JSON-результата
3. Строит сводный HTML-dashboard
4. Если модуль упал или отсутствует — graceful skip с пометкой «не выполнен»

## Когда использовать

- Presale полный аудит клиента (4 фактора вместо одного коммерческого)
- Quarterly review с динамикой по всем направлениям
- Сравнение с 1-3 конкурентами
- Базовая диагностика перед стратсессией

## Когда НЕ использовать

- Одностраничный лендинг — текстовые/ссылочные дадут мало сигналов
- Сайт без истории (<3 мес) — поведенческие факторы не собрать

## Workflow

```
URL → run_all.py → [4 модуля параллельно] → 4 JSON + 4 HTML
                                             ↓
                                    merge_report.py → dashboard.html
```

## Запуск

```bash
cd /Users/antonk/.claude/skills/seo-factors-audit

# Базовый прогон
./venv/bin/python scripts/run_all.py \
    --domain avto.world \
    --client avtoworld

# С конкурентами + параллельно
./venv/bin/python scripts/run_all.py \
    --domain avto.world \
    --client avtoworld \
    --competitors site2.ru,site3.ru \
    --parallel
```

### Выход

```
reports/avtoworld/
├── seo-audit-2026-04-17.html           ← сводный dashboard (СНАЧАЛА ЭТОТ)
├── commercial-2026-04-17.{json,html}
├── text-2026-04-17.{json,html}
├── link-2026-04-17.{json,html}
└── behavioral-2026-04-17.{json,html}
```

## Стандарт JSON-интерфейса модулей

Каждый модуль обязан выдавать JSON со следующими обязательными полями:

```json
{
  "module": "commercial",
  "domain": "avto.world",
  "date": "2026-04-17",
  "score": 67,
  "factors": [
    {"id": "f001", "name": "Телефон в шапке", "weight": 10,
     "passed": true, "status": "pass", "detail": "+7..."}
  ],
  "critical_issues": [
    {"factor_id": "f012", "name": "...", "severity": "high", "impact": "..."}
  ],
  "recommendations": [
    {"priority": "high", "action": "...", "effort": "low", "impact": "high"}
  ]
}
```

`score` модуля = `sum(weight * passed) / sum(weight) * 100`, округляем до целого.

Общий score dashboard = взвешенное среднее (веса по умолчанию 25/25/25/25, настраиваются через `--weights comm=30,text=25,link=25,behav=20`).

## Цветовая кодировка

| Диапазон | Цвет | Смысл |
|----------|------|-------|
| 0-40     | red (`#d82b63`) | Критические разрывы, срочно |
| 41-70    | yellow (`#e5a100`) | Средний уровень, план на квартал |
| 71-100   | green (`#059856`) | Ок, улучшения по остаточному принципу |

## Структура

```
seo-factors-audit/
├── SKILL.md
├── scripts/
│   ├── run_all.py           # запуск 4 модулей (последов/параллел)
│   └── merge_report.py      # 4 JSON → dashboard HTML
├── templates/
│   └── dashboard.html.j2    # CAMEO-стиль (обложка + 4 секции + план)
├── reports/                  # выходные отчёты по клиентам
└── logs/                     # логи прогонов
```

## Graceful skip

Если модуль не установлен или упал:
- В dashboard его секция помечается `не выполнен, см. лог`
- Общий score считается только по успешным модулям, в header пишется `(3/4 модулей)`
- В лог пишется причина (exit code, stderr)

## Интеграция

| Скилл | Связь |
|-------|-------|
| `commercial-factors-audit` | Модуль 1, запускается из `run_all.py` |
| `text-factors-audit` | Модуль 2 |
| `link-factors-audit` | Модуль 3 |
| `behavioral-factors-audit` | Модуль 4 |
| `presale-kp` | Executive summary из dashboard → слайд «Разрывы» |
| `factcheck-v2.py` | Обязательная проверка HTML перед отправкой клиенту |
| `seo-master` | Вызывает этот скилл как Module «Full Audit» |

## Бренд

- Отчёт подписан **artvision.pro** (строчные + `.pro`)
- Публичное название: **artvision.pro Pulse**
- Запрещено: AI / нейросеть / ML / LLM
- Используем: «авторская методология», «экспертный анализ», «методика»

## Подводные камни

- SPA без SSR → текстовые факторы будут фейлить. Предупредить клиента.
- Региональные редиректы → домен подавать с нужным регионом (`/msk/`).
- Модули с разными таймаутами → агрегированный прогон ~5-15 мин на клиента.
- Поведенческие факторы требуют доступа к Метрике — если нет, модуль работает по proxy-сигналам.

## Roadmap

- [ ] v0.2 — Сравнительный режим с 3+ конкурентами в одном dashboard
- [ ] v0.3 — PDF-экспорт dashboard через Playwright
- [ ] v0.4 — Автотригер из `/combine` по расписанию (quarterly)
- [ ] v0.5 — Интеграция с Метрикой (OAuth) для поведенческих
