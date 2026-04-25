# Handover: Карта Топов MVP — продукт Artvision Radar

**Дата:** 2026-04-25 22:00
**Контекст:** products
**Сессия:** ba647c6a (resume → 96299214)
**Статус:** в работе (MVP v1 задеплоен, накоплен backlog 10 фич)

## 🎯 Цель сессии

Антон вспомнил продукт «Карта Топов» (КАРТА 2: занятость ТОПа Яндекса по регионам РФ) → собрать MVP на реальных данных одного клиента → задеплоить на artvision.pro в нативном дизайне.

## ✅ Что сделано

- `products/karta-topov/collect_data.py` — Topvisor API → JSON pipeline (исправил v2 API: `date1/date2` вместо `dates`, парсинг ключа `YYYY-MM-DD:project:region`)
- `products/karta-topov/index.html` — MVP с SVG-картой РФ (упрощённый bbox + 6 точек городов), редизайн под artvision.pro: Manrope/Rubik, #614ce1 фиолетовый, светлая тема, hero-секция, hover-эффекты, CTA
- `products/karta-topov/data.json` — снапшот: 85 ключей × 6 регионов × 60 дней (2026-02-25 → 2026-04-26)
- **Деплой:** https://artvision.pro/karta-topov-demo/ (на VPS 80.90.181.152, путь `/var/www/artvision/karta-topov-demo/`)
- Источник данных подтверждён: **Topvisor API** (бесплатное чтение истории, без `--start-check`)

## 📊 Реальные данные первой карты (extru-tech-tpk.ru, project 18754493)

| Регион | Avg pos | ТОП-10 |
|--------|---------|--------|
| Москва | 8.3 | 70/83 |
| СПб | 9.9 | 67/82 |
| Екатеринбург | 9.8 | 65/82 |
| Н.Новгород | 10.1 | 65/82 |
| Новосибирск | 10.3 | 65/83 |
| Челябинск | 10.5 | 65/83 |

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Взять extru-tech-tpk вместо burenie-skv | burenie-skv 19788274 | extru-tech 18754493 уже имеет 6 регионов в Topvisor, burenie — только МСК |
| Чтение истории без `--start-check` | Запустить платную проверку | Данные за 60 дней есть бесплатно через `get/positions_2/history` с date1/date2 |
| Своя обёртка `collect_data.py` | Использовать готовый `topvisor_multiregion.py` | Готовый скрипт устарел: `dates: [date]` вместо `date1/date2`, парсит positionsData по старому формату → возвращал 0 записей |
| SVG bbox + точки городов | Реальный GeoJSON РФ | MVP за 1ч; контуры регионов — v2 |
| Google Fonts (Manrope+Rubik) | Системный стек | Демо для презентации Владу, не offline-клиент HTML; нативный дизайн artvision.pro важнее правила html-clients.md |
| Редизайн отдельным шагом | Сразу в artvision-стиле | Антон сначала захотел увидеть «есть данные?», потом «сделай в дизайне» — итеративный workflow |

## ❌ Что НЕ сделано (накоплено за 3 минуты в Dumb Zone)

10 фич backlog от Антона (приоритет HIGH→LOW):

1. **Карты для всех Topvisor-проектов с 2+ регионов** — фоновая задача `python3 .../topvisor.../scan` запущена, результат `/tmp/karta-topov-candidates.json` (на момент handover scan возможно ещё работает; перед стартом проверить `cat /tmp/karta-topov-candidates.json` — если пусто → перезапустить скрипт из секции «Команды воспроизведения»)
2. **Фильтр: только активные платящие клиенты** — пересечь candidates с реестром в `.claude/rules/clients-registry.md` (9 платящих)
3. **Индекс-страница** со списком клиентов
4. **Gap-анализ:** регионы Topvisor vs регионы на сайте клиента (NAP, контакты) → если на сайте регион есть, в Topvisor нет → добавить регион + предложить запуск платной проверки
5. **Реальная карта РФ как Wordstat** — контуры регионов с заливкой (нужен GeoJSON `russia-regions.json` упрощённый, ~50 КБ)
6. **Фильтр по кластерам** ключевых слов (использовать `groups` из Topvisor проекта)
7. **Кластеры в каждом регионе** с позициями
8. **Контакты клиента в регионах** (NAP) — наложение на карту
9. **Наложение Wordstat-спроса (КАРТА 1)** — Wordstat API регионы, регион-индекс
10. Pivot CSV-экспорт по регионам (как `topvisor_multiregion.py --csv`)

## 📚 Уроки

- **`scripts/topvisor_multiregion.py` устарел** — API ответ возвращает `positionsData` как dict с ключами `YYYY-MM-DD:project_id:region_index`, а скрипт ждёт старый формат. Записать в `feedback_topvisor_api_v2_format.md` или обновить сам скрипт. Параметры: `date1`/`date2`, не `dates: [date]`.
- **При работе с продуктом по эскизу** — Антон может за 2-3 минуты накидать 10 фич; в Dumb Zone (>60% контекста) НЕ продолжать, а ставить handover + новую сессию. Иначе будут ошибки. Эта сессия пробила 91%.
- **Дизайн-система artvision.pro** уже извлечена в `clients/artvision-pro/design-system.md` (Manrope+Rubik, #614ce1, градиенты 135deg) — переиспользовать для всех демо/промо страниц на нашем VPS.

## 🔜 Следующие шаги для новой сессии

**ВАЖНО — порядок:**

1. **HIGH:** Прочитать `/tmp/karta-topov-candidates.json` (если есть) → пересечь с реестром платящих → выбрать топ-3 проекта → запустить `collect_data.py` для каждого → сгенерить HTML из шаблона `products/karta-topov/index.html` (надо параметризовать через `?project=ID`)
2. **HIGH:** Создать индекс `/karta-topov-demo/index.html` со списком клиентов (карточки)
3. **MEDIUM:** Скрипт сравнения регионов сайта vs Topvisor — взять NAP из `clients/<name>/linkbuilding/nap-profiles-*.md` или scrape footer сайта → diff с регионами Topvisor → отчёт
4. **MEDIUM:** Реальная карта РФ — найти упрощённый GeoJSON (Natural Earth 1:50m → simplify через mapshaper до ~50KB)
5. **LOW:** Фильтр по кластерам — Topvisor `get/keywords_2/groups` по проекту
6. **LOW:** Wordstat-спрос (КАРТА 1) — wordstat API регионы, тепловая заливка под нашими точками

## 🗺️ Карта файлов

```
artvision-data/
├── products/karta-topov/
│   ├── collect_data.py    ← Topvisor API → JSON
│   ├── index.html         ← MVP, дизайн artvision.pro
│   └── data.json          ← extru-tech снапшот
├── products/karta-topov-idea.md   ← оригинальная идея 2026-02-07
├── goals/GOAL_karta-topov-product_2026-02-07.md   ← якорь цели
└── scripts/topvisor_multiregion.py   ← УСТАРЕЛ, не использовать как есть
```

VPS: `root@80.90.181.152:/var/www/artvision/karta-topov-demo/` (index.html + data.json)

## ⚠️ Gotchas

- **`topvisor_multiregion.py` возвращает 0 записей** даже если данные есть — НЕ доверять, использовать `collect_data.py`
- **`add/positions_2/searchers_regions` ругается** «нет region_key» при batch-вызове — это известный баг. Регионы добавляем по одному либо через UI Topvisor.
- **Без `--start-check`** API отдаёт только историю. Свежей сегодняшней проверки нет — последние данные на 2026-04-22 для extru-tech.
- **`html-clients.md` запрещает Google Fonts** для клиентских HTML; для нашего демо на artvision.pro — разрешил, потому что сайт сам грузит эти же шрифты. Не путать с КП клиентов.
- **Контекст 91%** при handover — следующая сессия должна стартовать с `/clear`, не `/compact`.
- **Background scan кандидатов:** ID `b0w0nv8cg`, output `/private/tmp/claude-501/-Users-antonk/01b09d4f-9d73-450f-b5c9-7b443baa5e1c/tasks/b0w0nv8cg.output` — может быть уже завершён к началу новой сессии.

## 💻 Команды воспроизведения

```bash
cd /Users/antonk/artvision-data

# Один проект
python3 products/karta-topov/collect_data.py --project 18754493 --days 60 \
  --out products/karta-topov/data.json

# Деплой
scp products/karta-topov/index.html products/karta-topov/data.json \
    root@80.90.181.152:/var/www/artvision/karta-topov-demo/

# Список всех проектов с 2+ регионами (если scan не завершился)
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from topvisor_multiregion import load_tokens, get_credentials, list_projects, get_project_regions
import json, time
tk = load_tokens(); uid, ak = get_credentials(tk)
out = []
for p in list_projects(ak, uid):
    rs = get_project_regions(p['id'], ak, uid)
    if len(rs) >= 2:
        out.append({'id': p['id'], 'site': p.get('site'), 'name': p.get('name'),
                    'regions': [{'idx': r.get('index'), 'name': r.get('name'), 'geoid': r.get('key')} for r in rs]})
    time.sleep(0.3)
json.dump(out, open('/tmp/karta-topov-candidates.json','w'), ensure_ascii=False, indent=2)
print(f'{len(out)} projects')
"
```

## 🔗 Связанные ресурсы

- Live demo: https://artvision.pro/karta-topov-demo/
- Идея: `products/karta-topov-idea.md` (2026-02-07, для встречи Влада Фемистоклова)
- Goal: `goals/GOAL_karta-topov-product_2026-02-07.md`
- Topvisor аккаунт: `tokens.json` → `topvisor.user_id` / `topvisor.api_key`
- Реестр клиентов: `.claude/rules/clients-registry.md` (9 платящих, в т.ч. Burenie-SKV, OTIDO, Geely A2Auto)

## 🔄 Переклассификация продукта (важно!)

Антон в конце сессии: **«это уже не Карта Топов — это общий мониторинг = наш продукт»**.

«Карта Топов» = один из view внутри **Artvision Pulse** (мониторинг) или **Artvision Flow** (SEO-конвейер). Решить в новой сессии.

## 🧮 Концепция: Priority Score (Hot Keys)

Развитие от Антона: не просто карта позиций, а **приоритизатор ключей** — какие двигать первыми, чтобы быстрее получить органику + поведенческие.

```
PriorityScore =
    Frequency_Wordstat
  × (1 − AggregatorShare_TOP10)         // мало агрегаторов = шанс есть
  × (1 − SpecPlacementCount/4)          // мало спецразмещения = выше орг. CTR
  × ContentStrength_avgTop10            // у конкурентов в ТОПе мало бэклинков → слабая ниша
  × ClusterAnchorWeight                 // маркерный (главный ключ кластера) = бонус
  × OurPositionProximity                // мы рядом с ТОПом → толкнуть проще
```

**ContentStrength** = `1/(avg_backlinks_TOP10 + 1)` — гипотеза Антона: страница в ТОПе с малым числом ссылок = сильный контент сам по себе → ниша где можно встать без линкбилдинга.

## 🧰 Инвентаризация: что уже есть в репо

ГОТОВО:
- `scripts/topvisor_serp.py` — SERP top-10 сбор
- `scripts/serp-cluster.py` — SERP-кластеризация (hard/soft, threshold)
- `scripts/seo-cluster.py` — embeddings-кластеризация
- `scripts/topvisor_validate_clusters.py` — валидация кластеров
- `scripts/topvisor_multiregion.py` — устарел (баг с positionsData parsing), использовать новый `products/karta-topov/collect_data.py`
- `scripts/semrush_backlink_gap.py` — Semrush Backlink Gap через Playwright
- `scripts/semrush_top_pages.py` — Semrush Top Pages (URL → traffic + backlinks)
- `scripts/direct_search_queries_monitor.py` — мониторинг запросов в Директе
- `scripts/direct_moderation_check.py` — модерация Директа
- Wordstat API — `tokens.json yandex.wordstat` + rule `.claude/rules/yandex-api.md`
- `dashboards/engine/modules/` — есть `traffic.py`, `marketplaces.py`, `tasks.py`, `competitors_finance.py` → сюда добавлять новые модули

НЕТ (доработка):
- **Aggregator detection** в SERP — нужен список доменов (wildberries, ozon, market.yandex, avito, zoon, 2gis, prom, dzen, …) и классификатор URL → пометка тип в `topvisor_serp.py` (наш/конкурент/агрегатор/маркетплейс/Дзен/соцсеть)
- **Spec placement count** Директа в выдаче — нет детекции (через Direct API spec-placement endpoint или scrape SERP-блока)
- **ContentStrength** — данные есть в Semrush, формулы как метрики нет
- **PriorityScore** агрегатор — нового скрипта `priority_score.py` нет
- UI-вьюшка ключей по приоритету — нет

## 🏗️ Целевая архитектура (план для новой сессии)

```
dashboards/engine/modules/
  ├── priority_engine.py   ← НОВЫЙ — собирает PriorityScore из готовых компонентов
  ├── serp_classifier.py   ← НОВЫЙ — детект агрегаторов/МП/Дзена в SERP (список доменов)
  ├── traffic.py           ← есть
  ├── marketplaces.py      ← есть
  └── ...

products/<pulse|flow>/regions/   ← возможно переименовать из products/karta-topov/
  ├── collect_data.py            ← уже есть
  ├── priority_score.py          ← НОВЫЙ — точка входа сборки
  ├── index.html                 ← view «Регионы» (готов)
  └── views/
      ├── hot-keys.html          ← view «Топ ключей по PriorityScore»
      ├── clusters.html          ← view «Кластеры»
      └── gap.html               ← view «Gap: регионы сайта vs Topvisor»
```

## 🔜 Дополнения к следующим шагам

(перенумеровать вместе с предыдущими 6 пунктами)

7. **Решение с Антоном:** Pulse или Flow? Одно слово, влияет на путь `products/<name>/`
8. **Pre-flight inventory** — перечитать `scripts/topvisor_serp.py` целиком (есть ли уже частично классификация SERP), `scripts/serp-cluster.py` (можно ли извлечь маркерный ключ из готовой кластеризации)
9. **`serp_classifier.py`** — список агрегаторных доменов + helper `classify_url(url) → tag` → дополнить `topvisor_serp.py` колонкой типа
10. **`priority_score.py`** — собирает все готовые куски в одну формулу. ВАЖНО: не дублировать сбор данных, читать готовые JSON из output/ скриптов выше.
11. **View «Hot Keys»** — рядом с картой регионов, таблица топ-20 ключей по `PriorityScore` для выбранного региона
12. **Кластерный фильтр** на UI — выбираешь кластер → метрики и список ключей пересчитываются

## 🎬 Состояние при закрытии

- ✅ git: незакоммичено (products/karta-topov/* + handover файл) — закоммитить в новой сессии
- ✅ VPS: задеплоено, доступно по URL
- 🔄 Background task `b0w0nv8cg` запущена, статус неизвестен на момент закрытия
- 📍 Next session: `cd ~/artvision-data && cat /tmp/karta-topov-candidates.json` → продолжить с этапа 1
