---
name: local-org-discovery
description: Pipeline для сбора и анализа локальных организаций (школы/клиники/детсады/услуги по городу или району). Параллельный рой 4 спецов, gov/commercial split, strict-factcheck, HTML-дашборд из template. Триггеры — выбор школы / выбор клиники / выбор детсада / организации района / local-org-discovery / организации в городе X / куда отдать ребёнка.
---

# Local Org Discovery — pipeline для выбора локальных организаций

> **Базис прецедента:** сессия SCHOOL 15.05.2026 — выбор школы Алины в Петроградском СПб. Артефакты: `~/artvision-data/personal/alina-school-petrogradsky/`.
> **Применяется к:** школам, клиникам, детсадам, фитнес-клубам, кружкам, услугам по городу или району. Везде где нужен системный compare локальных организаций с учётом отзывов, госу/комм статуса, объективных рейтингов.

## Когда вызывать

Триггеры (любой):
- `/local-org-discovery <город> <район> <тип> [для кого]`
- «выбор школы / клиники / детсада»
- «организации в городе X», «куда отдать ребёнка»
- «куда обратиться по теме Y в районе Z»

**Пример:** `/local-org-discovery СПб Петроградский школы для Алины 6 лет`

## Входные данные

Обязательные:
- **{город}** — Санкт-Петербург / Москва / Казань / Уфа / ...
- **{район}** — конкретный административный или микрорайон. Если не задан — спросить или взять весь город.
- **{тип организации}** — школы / клиники / детсады / стоматологии / фитнес / автосервисы / ...

Опциональные:
- **{для кого}** — возраст ребёнка / диагноз / специфика. Влияет на фильтры и веса.
- **{base path}** — куда складывать. Дефолт: `personal/<topic-slug>/`.

Если что-то критичное отсутствует — задать 1-2 уточняющих вопроса (`AskUserQuestion`), не больше. Дальше — выполнять.

## Выход (что генерирует skill)

### 1. JSON-файлы данных в `<base>/data/`

| Файл | Источник | Спец |
|------|----------|------|
| `seed-orgs.json` | WebSearch + 3-5 топ-агрегаторов города | главный (этот skill) |
| `orgs-yandex.json` | Я.Карты прямой fetch + city_verified | data-researcher #1 |
| `orgs-aggregators.json` | 2GIS + Zoon + локальный каталог | data-researcher #2 |
| `social-research.json` | VK + TG public preview | data-researcher #3 |
| `objective-ratings.json` | RAEX/Фонтанка/проф.рейтинги (если применимо) | data-researcher #4 |

### 2. HTML-дашборд

`<base>/analysis-<YYYY-MM-DD>.html` — из template `~/.claude/templates/personal-decision-dashboard.html`.

### 3. Опциональный deploy

На `artvision.pro/preview/<topic-slug>/` если пользователь явно просит. Иначе только локальный файл.

## Pipeline — 8 шагов

### Шаг 1. Seed-list (~3-5 мин)

1. Определить **slug** для папки. Конвенция: `<кто или регион>-<тип>-<район>` латиницей. Пример: `alina-school-petrogradsky`, `marina-clinic-vasileostrovsky`.
2. Создать структуру: `mkdir -p <base>/{data,reports,screens}`.
3. Найти топ-3..5 **городских агрегаторов** для типа:
   - Школы СПб: `apeterburg.com` + `shkola.city`
   - Клиники: `prodoctorov.ru` + `zoon.ru` + `napopravku.ru`
   - Детсады СПб: `apeterburg.com` (раздел детсады) + `littleone.ru`
   - Универсал: `2gis.ru` + `yandex.ru/maps` + `zoon.ru`
4. Через `WebSearch` собрать **seed-list** организаций района (целиться на 15-25 штук).
5. Записать в `<base>/data/seed-orgs.json` (схема — см. `data-schema.json`).

### Шаг 2. Параллельный рой 4 спецов

Запускать через `Task` tool, `subagent_type: "general-purpose"`, `run_in_background: false` (нужно все 4 результата для шага 3). Промпты — в `agent-prompts/`:

| # | Агент | Prompt-файл |
|---|-------|-------------|
| 1 | yandex-maps | `agent-prompts/01-yandex-maps.md` |
| 2 | aggregators (2GIS + Zoon + local) | `agent-prompts/02-aggregators.md` |
| 3 | social (VK + Telegram) | `agent-prompts/03-social.md` |
| 4 | objective ratings | `agent-prompts/04-objective.md` |

Каждый промпт получает на вход путь к `seed-orgs.json` и пишет результат в свой JSON-файл. Параллельный запуск ВСЕХ 4 в одном сообщении.

**Важно:** все 4 спеца — **общая база `general-purpose`** с Bash + WebSearch + WebFetch. НЕ запускать без Bash — без HTTP-проверок данные = галлюцинации (см. `quality.md` блокер R3).

### Шаг 3. City-verification

После сбора `orgs-yandex.json` — каждый Я.Карты URL проверить:
1. WebFetch URL → парсить title + meta
2. Проверить что в названии/адресе фигурирует target-город
3. Если найден другой город (как СОШ 91 = Ижевск в прецеденте) — пометить `city_verified: false` и **исключить из дашборда**

Hook `~/.claude/hooks/pre-yandex-maps-place-check.sh` уже блокирует подмены при Edit/Write. Проверить наличие маркера `city_verified` в каждой записи.

Связано: memory `feedback_yandex_place_city_mismatch.md` (если есть в репо).

### Шаг 4. Gov vs Commercial split

Автоматически разметить тип через name regex:
- **Государственные:** `ГБОУ|ГБУЗ|МБОУ|МАОУ|МУП|ГБУ|ФГБОУ|МКУ|СПб ГБУ` → `org_type: "gov"`
- **Коммерческие:** `ООО|ИП|АНО|ЧОУ|ЧУ` или известные сети без госаббревиатур → `org_type: "commercial"`
- **Частная без юр.формы в названии:** искать ИНН/ОГРН через WebSearch — определить по реестру.

Записывать в `org_type` поле каждой организации. См. memory `feedback_reviews_gov_vs_commercial_split.md` — отзывы гос/комм нельзя сравнивать в лоб (разный профиль критики).

### Шаг 5. NLP-темы +/-

Из собранных отзывов агенты #1, #2, #3 должны вытащить:
- **themes_positive** — топ-3..5 тем «хвалят» по сегменту И по каждой организации
- **themes_negative** — аналогично «ругают»
- **Временной разрез** обязателен:
  - `delta: "+"` — усиливается
  - `delta: "-"` — затихает
  - `delta: "новое"` — появилось в 2024-2026
  - `delta: "стабильно"` — без изменений
  - `year: "2024-2025"` — пик/появление темы

Группировать темы по: преподаватели/врачи/руководство, здание/санитария, программа/качество, цена/поборы, дисциплина/конфликты.

### Шаг 6. Strict-factcheck (GATE)

Перед deploy и финальной выдачей пользователю — **обязательный** прогон:

```
Agent(
  subagent_type: "strict-factchecker",
  prompt: "Проверь HTML-дашборд <path>/analysis-<date>.html. Источники в <path>/data/. Особое внимание: city_verified=true для всех орг., числа отзывов = реальные из JSON, темы +/- имеют источник."
)
```

Если CRITICAL > 0 — НЕ показывать пользователю до фикса. См. `~/.claude/rules/quality.md`.

### Шаг 7. HTML-дашборд из template

1. Скопировать `~/.claude/templates/personal-decision-dashboard.html` → `<base>/analysis-<YYYY-MM-DD>.html`
2. Заменить контент по секциям:
   - **Hero** — заголовок, для кого, дата, источники, дисклеймер (методология, captcha-rate, ограничения)
   - **Tier S/A/B/C/Spc** — финальная сегментация (Spc = специализированные / частные)
   - **Матрица сравнения** — таблица: org × (рейтинг, отзывы, темы +/-, тренд)
   - **Heatmap** — рейтинги по агрегаторам (Я.Карты / 2GIS / Zoon / прочее)
   - **Bar chart** — отзывы по объёму
   - **Trust 2x2** — официальные данные vs реальные отзывы (где гэп)
   - **Drill-down карточки** — по каждой организации: VK link, ключевые темы +/-, динамика 2018-2026, рекомендация
   - **Дерево решений** — практические сценарии «если хочешь X → выбирай Y»

Template — **готовый CSS + структура**, не переписывать. Только инжектить данные.

### Шаг 8. Deploy + visual validation (опционально)

Если пользователь явно просит «деплой» / «на сервер» / «показать всей семье»:

1. `scp` на VPS: `artvision.pro/preview/<topic-slug>/`
2. `X-Robots-Tag: noindex, nofollow` через `.htaccess` (правило `security.md`)
3. `Agent(subagent_type: "ui-visual-validator", prompt: "screenshot 375/768/1024/1440 https://artvision.pro/preview/<slug>/")`
4. Если ui-validator нашёл проблемы — пофиксить и redeploy.

## Связанные правила и материалы

- `~/.claude/rules/quality.md` — gates per task-type, blocker R3 (Bash для HTTP-валидации)
- `~/.claude/rules/factcheck.md` *(если есть)* / skill `/factcheck`
- `~/.claude/rules/security.md` — X-Robots-Tag, табу AI в публичных материалах
- `~/.claude/rules/no-smoothing.md` — без сглаживания в выводах
- Memory: `feedback_reviews_gov_vs_commercial_split.md` (если есть)
- Hook: `~/.claude/hooks/pre-yandex-maps-place-check.sh` — city-verify guard
- Template: `~/.claude/templates/personal-decision-dashboard.html`
- Schema: `~/.claude/skills/local-org-discovery/data-schema.json`

## Антипаттерны

| ❌ | ✅ |
|---|---|
| Запустить 4 агентов с `research-analyst` (нет Bash) | `general-purpose` со всеми тулзами |
| Принять Я.Карты URL без city-verify | WebFetch + парс title + проверка target-города |
| Сравнить отзывы ГБОУ и частной школы в лоб | Gov/commercial split, разные веса |
| Показать пользователю без factcheck-gate | `strict-factchecker` обязательно |
| Делать вывод о тренде из 1 снимка | Минимум 2 замера в разное время или интервал отзывов 2-3 года |
| Записать «AI собрал данные» в дашборд | «Авторская методология», «аналитический разбор открытых источников» |
| Деплой без `noindex, nofollow` | Обязательно для всех `personal/*` страниц |

## Прецедент

**15.05.2026, сессия SCHOOL** — выбор школы для Алины 6 лет в Петроградском СПб.
- Артефакт: `~/artvision-data/personal/alina-school-petrogradsky/analysis-2026-05-15.html`
- Данные: 4 JSON в `data/` (seed + yandex + social + objective)
- Captcha-rate Я.Карт: 85% (18 из 21 школ), fallback на apeterburg + 2GIS + shkola.city + schoolotzyv
- Подмена места: СОШ 91 на Я.Картах оказалась в Ижевске — city-verify поймал
- Результат: tier S/A/B/C + Spc сегментация, дерево решений по сценариям семьи

## Контрольный пример вызова

```
/local-org-discovery Казань Вахитовский стоматологии для взрослых
```

Skill:
1. Создаёт `personal/kazan-stom-vahitov/{data,reports,screens}/`
2. Сидит через `prodoctorov.ru` + `zoon.ru/kazan` + `2gis.ru/kazan` → `seed-orgs.json` (~20 клиник)
3. Параллельно: 4 спеца → Я.Карты Казань + 2GIS Казань + VK Казань + Минздрав РТ рейтинги
4. City-verify (исключает любую клинику не в Казани)
5. Gov vs commercial (ГАУЗ vs ООО)
6. NLP-темы +/- с временным разрезом 2022-2026
7. strict-factchecker gate
8. HTML-дашборд `analysis-2026-05-15.html` + опционально deploy на `artvision.pro/preview/kazan-stom-vahitov/`

Время полного прогона: ~25-40 мин в зависимости от captcha-rate и числа орг.
