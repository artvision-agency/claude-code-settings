---
name: project-gantt
description: >
  Сборка ГАНТа работ по дням для клиента/проекта по единому шаблону Artvision (как USmile).
  Источник правды — Asana (задачи проекта) + worklist клиента, поэтому ГАНТ соотносится с OPS.
  Клиентский артефакт: БЕЗ имён исполнителей, услуга = полный комплекс, бренд Artvision, mobile-first.
  Триггеры: «project-gantt», «гант по дням», «гант проекта», «сделай гант как у usmile», «план-чарт клиенту»,
  «day gantt», «gantt по дням <клиент>».
---

# project-gantt — ГАНТ работ по дням (шаблон Artvision)

Делает день-в-день ГАНТ работ для клиента по единому формату (эталон — USmile, июнь 2026).
**Главное: ГАНТ соотносится с OPS+Asana** — задачи на чарте = задачи в Asana проекта = строки worklist.

## Вызов
```
/project-gantt <slug> [месяц]
# примеры:
/project-gantt grelka-gudelka июнь
/project-gantt usmile
```
Или фразой: «сделай гант по дням <клиенту> как у usmile».

## Источник правды (ОБЯЗАТЕЛЬНО — связка с OPS+Asana)

ГАНТ НЕ выдумывается. Строки чарта = **синхронизация трёх источников**:
1. **Asana** проекта клиента (`mcp__asana__asana_search_tasks` / `get_tasks_for_project`, проект «Задачи - Artvision» 1212305892582815 или проект клиента) — задачи с `due_on` → бары на ГАНТе по датам.
2. **`clients/<slug>/plan/work-assignment-asana-*.md`** (worklist) — состав работ + сроки + (внутренне) исполнители.
3. **Договор** (`clients/<slug>/legal/`) — услуга = полный комплекс (предмет договора), не один подраздел.

Если в Asana ещё нет задач проекта — сначала завести их (правило `asana-required-fields.md`: assignee явно/спросить + due_on + project_id), потом строить ГАНТ из них. ГАНТ и Asana должны совпадать по датам и составу.

## Алгоритм
1. **Pre-Task Read** клиента (`clients/<slug>/` CLAUDE.md + context-log + config.yaml + work-assignment).
2. **Собрать задачи из Asana** проекта (due_on, название, направление) → нормализовать в строки (направление → день-старт → день-конец).
3. **Сверить с worklist + договором** — услуга показывается ПОЛНЫМ составом (SEO: аудит+семантика+внутренняя+off-page/каталоги+реструктуризация+страницы; PPC: настройка по этапам; соцсети: ведение+реклама+посевы). НЕ сужать.
4. **Заполнить шаблон** `~/artvision-data/templates/project-gantt/gantt-template.html`:
   - дни 1–N месяца + выходные (рассчитать на нужный месяц в `<script>` массив `we`)
   - фазы (направления) + бары (left%/width% = (день−1)/N*100)
   - старт-маркер ▶ на ключевой дате
   - бренд Artvision в шапке/футере
5. **Рендер PNG** через `render-day.cjs` (Playwright, 1280px, deviceScaleFactor 2).
6. **Deploy** на `artvision.pro/<slug>-test/plan/` (HTML+PNG) + хаб-страница со ссылками.
7. **Проверка** (factcheck-lite): нет имён исполнителей · услуга полным составом · нет внешних URL · HTTP 200.

## Жёсткие правила клиентского ГАНТа (rule `client-plan-no-assignees-full-scope.md`)
- ❌ НЕ показывать имена исполнителей (Антон/Андрей/Стас) — это для заказчика. Исполнители живут в Asana/worklist.
- ✅ Услуга = ПОЛНЫЙ комплекс работ (как предмет договора), не один подраздел.
- ✅ Структуры списками (document-list-format), бренд Artvision (branding-policy), mobile-first (mobile-first-all-html).
- ✅ Блокеры (ждём доступ/контент) — приглушённый бар + пометка 🔒.

## Шаблон и эталон
- Шаблон: `~/artvision-data/templates/project-gantt/gantt-template.html` + `render-day.cjs`
- Эталон-референс: `clients/usmile/plan/gantt-usmile-june-days.html` (палитра фаз, выходные, старт-маркер)
- 6-мес горизонт (опц.): `clients/usmile/plan/gantt-usmile.html`

## CSS-параметры баров (как считать)
- `left% = (день_старта − 1) / дней_в_месяце × 100`
- `width% = (день_конца − день_старта + 1) / дней_в_месяце × 100`
- выходные июня 2026: `[6,7,13,14,20,21,27,28]` — пересчитать для своего месяца
- цвета фаз: --seo #4f8cff · --ads #ff7a59 · --soc #7c5cff · --tg #3aa6ff · --off #e0567a · --rep #19c37d

## Связь
- `asana.md` + `asana-required-fields.md` — задачи Asana = источник
- `client-plan-no-assignees-full-scope.md` — без исполнителей + полный комплекс
- `project-work-plan-template.md` — task-plan.md + визуал (этот ГАНТ = визуал)
- `branding-policy.md`, `document-list-format.md`, `mobile-first-all-html.md`
