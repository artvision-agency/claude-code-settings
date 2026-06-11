---
name: client-monitor
description: "Мониторинг клиентов: позиции Topvisor, динамика по неделям, топ-проседаний и ростов, бриф для созвона. Триггеры: 'мониторинг', 'позиции клиентов', 'динамика', 'бриф для звонка', 'client monitor', 'позиции топвизор', 'мониторинг na-sklad', 'мониторинг zakvaski-rus'"
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebFetch
---

# Client SEO Monitor

## Что делает

1. Подтягивает позиции клиента из Topvisor (read-only API, БЕЗ запуска `checker/go`)
2. Сравнивает с прошлой неделей (или ближайшим доступным снимком за 60 дн.)
3. Выводит Топ-5 проседаний (Δ ≥ 5 позиций вниз) и Топ-5 ростов (Δ ≥ 5 вверх)
4. Считает общую динамику (выросло/упало/стабильно + TOP-10 вход/выход)
5. Генерирует бриф для созвона с клиентом

## Источники project_id

Скрипт читает в порядке приоритета:

1. CLI флаг `--project-id N` (явный override)
2. `clients/<slug>/topvisor_project_id.txt`
3. `clients/<slug>/presale/seo/topvisor_project_id.txt`
4. `schedule/reports-invoices.json` → `reports_and_invoices.<slug>.topvisor_project_id`

Известные проекты:
- `na-sklad` → 28545848 (СПб lr=2 default, region_index=3)
- `zakvaski-rus` → 28182826
- `burenie-skv` → 19788274 (платящий клиент, регион=1 Москва)
- `taller` → 16374958 (СПб)
- `anzhee-clinic` → 12304932 (СПб)
- `geely-a2auto` → 25066710
- `extru` → 18754493
- остальные платящие — см. `schedule/reports-invoices.json`

## Запуск

### Полный pipeline (snapshot + сравнение + бриф)

```bash
cd /Users/antonk/artvision-data
python3 scripts/client_topvisor_positions.py <slug>
```

Snapshot сохраняется в `clients/<slug>/seo/positions/YYYY-MM-DD.json`.

### Markdown-бриф для созвона

```bash
python3 scripts/client_topvisor_positions.py <slug> --markdown
```

### JSON для дальнейшей обработки

```bash
python3 scripts/client_topvisor_positions.py <slug> --json
```

### Опции

| Флаг | Описание |
|------|----------|
| `--project-id N` | Принудительно указать project_id (override автодетекта) |
| `--weeks-back N` | Сколько недель назад искать для сравнения (default 1) |
| `--no-save` | Не сохранять snapshot в `clients/<slug>/seo/positions/` |
| `--json` | Вывод в JSON |
| `--markdown` | Вывод полного Markdown-брифа |

### Bypass хуков (если skill вызывается вручную)

Скрипт затрагивает SEO-пути, поэтому могут сработать:
- `pre-tool-seo-task-require-master.sh` → требует Skill `/seo-master` сначала
- `pre-seo-task.sh` → требует свежие SF/Lighthouse артефакты <7 дней

Для read-only мониторинга:
```bash
env SEO_MASTER_FORCE=1 SEO_FRESH_SKIP=1 \
    python3 scripts/client_topvisor_positions.py <slug>
```

## Старый workflow (массовый мониторинг)

Старый `client_monitor.py` с захардкоженным списком клиентов остаётся для cron:

```bash
python3 scripts/client_monitor.py --check --report --brief
```

⚠️ `--check` запускает `checker/go` — это **тратит баланс Topvisor**. Использовать только по расписанию или вручную с пониманием стоимости. См. `~/.claude/projects/-Users-antonk/memory/feedback_topvisor_filter_safety.md`.

## Формат вывода (Markdown brief)

```
# Топвизор-бриф: <slug>

- Снимок: 2026-05-18
- Сравнение с: 2026-05-12
- Регионы: [1]
- Всего ключей: 269

## Текущие метрики
- Средняя позиция: 11.7
- TOP-10: 181 / 264
- TOP-30: 231 / 264

## Динамика (vs прошлая неделя)
- 📈 Выросло: 101 / Упало: 75 / Стабильно: 89
- TOP-10 вход: +27 / выход: -16

## 🔴 Топ-5 проседаний (alert)
| Ключ | Было | Стало | Δ | Частотность |
...

## 🟢 Топ-5 ростов
...

## 📋 Бриф для созвона
- ⚠️ 38 ключ(ей) просели >5 позиций — обсудить причины
- ✅ 45 ключ(ей) выросли >5 позиций — показать клиенту
- 📈 Общий тренд позитивный (+26 к балансу) — расширить договор
```

## Интерпретация результатов для переговоров

| Тренд | Что говорить клиенту |
|-------|----------------------|
| 📈 trend +20 и больше | Показать результат, предложить расширение, upsell |
| 📉 trend -20 и больше | Алерт команде, обсудить причины с клиентом, предложить аудит |
| Много проседаний >5 поз. | Разобрать конкретные ключи, проверить технику сайта |
| Много ростов в TOP-10 вход | Кейс для портфолио + расширение договора |
| Нет данных для сравнения | Первый snapshot или slot пустой — предложить базовый аудит |

## Важные ограничения (read-only только)

⚠️ **НИКОГДА** не запускать `checker/go` через этот pipeline — деньги списываются за съём по проектам. См. memory `feedback_topvisor_filter_safety.md` (прецедент 29.04 — 100 RUB за 2 broadcast).

Используем только эти эндпоинты (read-only, бесплатные):
- `get/positions_2/history` — текущие и прошлые позиции
- `get/keywords_2/keywords` — список ключей с volume и тегами
- `get/projects_2/projects` — метаданные проекта (для resolve регионов)

## Известные quirks Topvisor API v2

См. `~/.claude/projects/-Users-antonk/memory/feedback_topvisor_api_v2_quirks.md`:

- Header `User-Id` (НЕ `X-User-Id`), `Authorization: bearer <key>` (lowercase)
- Регионы подхватываются АВТОМАТИЧЕСКИ если у аккаунта `dune87@yandex.ru` настроены defaults (СПб lr=2 + Москва lr=213 + Екатеринбург)
- `get/positions_2/history` хранит snapshots не каждый день — скрипт ищет ±3 дня вокруг target, fallback за 60 дней
- `result` бывает строкой, не объектом — `_extract_id()` должен поддерживать int(str)

## Структура файлов

```
clients/<slug>/
├── topvisor_project_id.txt        # ID проекта (если не в schedule/reports-invoices.json)
├── presale/seo/topvisor_project_id.txt  # альтернативное место для presale
└── seo/
    ├── positions/                  # snapshot'ы — продукт client_topvisor_positions.py
    │   ├── 2026-05-18.json
    │   ├── 2026-05-20.json
    │   └── ...
    └── weekly/                     # старая еженедельная агрегация (seo_weekly_monitor.py)
```

## Cron (еженедельно)

```bash
# ПН 08:00 — снимок позиций + бриф в TG для всех клиентов из schedule/reports-invoices.json
0 8 * * 1 cd /Users/antonk/artvision-data && \
  for slug in na-sklad zakvaski-rus burenie-skv geely-a2auto; do \
    SEO_MASTER_FORCE=1 SEO_FRESH_SKIP=1 \
      python3 scripts/client_topvisor_positions.py "$slug" --markdown \
      >> /tmp/client-monitor-$(date +\%F).md ; \
  done
```

(Существующий `seo_weekly_monitor.py` уже шлёт TG-дайджест автоматически — этот pipeline дополняет его детализированными брифами.)

## Связанные скрипты

- `scripts/client_monitor.py` — старый монитор с `checker/go` (платный)
- `scripts/client_topvisor_positions.py` — новый read-only pipeline (этот skill)
- `scripts/seo_weekly_monitor.py` — еженедельный TG-дайджест
- `scripts/seo_position_monitor.py` — базовые классы `TopvisorAPI`/`PositionAnalyzer` (используются)
- `scripts/lib/topvisor_utils.py` — резолв регионов (3-tier fallback)
