---
name: combine
description: |
  Комбайн — непрерывный конвейер: ОЧЕРЕДЬ → ВЫПОЛНЕНИЕ → ПРОВЕРКА → ПУБЛИКАЦИЯ → ЗАКРЫТИЕ.
  НЕ останавливается между шагами. Единственная пауза = CONFIRM-уровень (security.md), собирается в батч в конце.
  Тянет из Asana + 5 TODO, дедуплицирует, читает контекст, сортирует, выполняет, верифицирует, деплоит, закрывает.
  Триггеры: комбайн, combine, harvester, конвейер, перемалывай, го
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Skill
  - mcp__asana__*
  - mcp__claude_ai_Asana__*
---

# Комбайн — Непрерывный конвейер

```
ОЧЕРЕДЬ → ВЫПОЛНЕНИЕ → ПРОВЕРКА → ПУБЛИКАЦИЯ → ЗАКРЫТИЕ
   │          │             │            │           │
   │          │             │            │           └─ Asana ✅ + TODO [x] + context-log + git
   │          │             │            └─ git/scp/WP/bot + post-deploy curl
   │          │             └─ factcheck URL + числа + DOM + screenshot + bot healthcheck
   │          └─ скилл по маршруту ([skill:X] > Asana-тег > эвристика)
   └─ pull + dedup + parse + sort + context
```

**ГЛАВНОЕ ПРАВИЛО: НЕ ОСТАНАВЛИВАТЬСЯ.**
Конвейер идёт задача за задачей. Единственная пауза = батч 🔴 CONFIRM в конце прогона.

---

## РЕЖИМЫ

| Команда | Поведение |
|---------|-----------|
| `комбайн` / `го` | Непрерывный: pull → execute → verify → publish → close |
| `комбайн план` | Только показать план, не выполнять |
| `комбайн [клиент]` | Только задачи конкретного клиента |
| `комбайн ревью` | Только анализ последнего прогона |
| `комбайн авто` | Фоновый cron-режим (09:30 + 18:00) |

---

## СХЕМА ЗАДАЧИ (единый формат)

Все задачи — из Asana и TODO — парсятся в единую структуру:

```yaml
id: <asana_gid | todo:file:line>
title: <глагол + объект>
source: asana | todo
client: <имя или null>           # [client:X] или projects/tags в Asana
product: <имя или null>           # [product:X]
skill: <имя скилла или null>      # [skill:X] (явный) — ПРИОРИТЕТ
priority: high | medium | low     # [priority:X] или by revenue
due: <YYYY-MM-DD или null>
blocked_by: <id или null>         # [blocked-by:X]
session: ops | bot | infra | presale | products  # [session:X] → cwd
human_only: bool                  # [human-only] или эвристика (встреча/звонок/перевод)
result_type: code | html | doc | deploy | asana-only | human
estimated_minutes: <число>        # классификация → таймаут
context_dir: <путь к CLAUDE.md или null>
confirm_level: auto | confirm     # по security.md
```

### Парсинг ключей

**Из TODO.md** — regex: `\[(\w+):([^\]]+)\]`. Поддерживаемые ключи: `client`, `product`, `skill`, `priority`, `blocked-by`, `session`, `result`, `human-only`, `estimate`.

**Из Asana:**
- `client` → по tags `client-*` или по `projects` (матч `clients/*/CLAUDE.md` name)
- `skill` → по tags `skill-*` или по ключевым словам в name/notes
- `priority` → по tags `priority-*` или по дедлайну (overdue → high)
- `session` → по projects (bot/infra/presale/products)
- `confirm_level` → по tags `confirm-*` или по security.md-правилам

Если пара ключ-значение не найдена → значение `null`, не блокер. Задача всё равно попадает в pipeline.

---

## PIPELINE (6 фаз, без остановок)

### ФАЗА 1: PULL + DEDUP + PARSE + CONTEXT

**1a. Тянем источники параллельно:**
```
mcp__asana__asana_search_tasks:
  workspace: 860693669973770
  completed: false
  sort_by: due_date
  opt_fields: name,due_on,projects,tags,notes,assignee,dependencies
```
+ читаем 5 TODO-файлов:
```
artvision-data/TODO.md
artvision-data/presale/TODO.md
artvision-data/products/TODO.md
artvision-tg-bot/TODO.md
devops-agent/TODO.md
```

**1b. Дедупликация (source of truth = Asana):**

Матч по двум сигнатурам:
1. Точный: `asana_gid` в TODO-строке (`[asana:GID]`)
2. Fuzzy: `slugify(title)` + `client` совпадают на 90%+ (Levenshtein)

Правила слияния:
- Задача в обоих местах → источник Asana, TODO-строка получает пометку `[asana:GID]` (AUTO)
- Задача только в TODO → создать в Asana (AUTO, AsanaRequiredFields применяются)
- Задача только в Asana → добавить строку в соответствующий TODO по `session`/`client`
- Конфликт статуса (TODO `[x]`, Asana open) → Asana выигрывает, TODO откатывается
- Конфликт `due_on` → Asana выигрывает

**1c. Парсинг в единую схему** (см. выше). Задачи без минимума (`title` + `result_type`) → в секцию `🟡 NOT READY`, не в pipeline, показать в отчёте.

**1d. Контекст для КАЖДОЙ задачи:**

```bash
# если есть client:
cat clients/<client>/CLAUDE.md          # правила
tail -50 clients/<client>/context-log.md # последние решения
ls clients/<client>/patches/             # известные ошибки

# если есть product:
cat products/<product>/CLAUDE.md

# если ничего нет (внутренняя задача):
# читаем PROJECTS.md секцию по session
```

CLAUDE.md клиента отсутствует → создать шаблон из `~/.claude/templates/client-CLAUDE.md`, записать в context-log что создан. НЕ блокировать задачу.

→ Результат: список задач со схемой и контекстом.
→ СРАЗУ ФАЗА 2.

### ФАЗА 2: СОРТИРОВКА + МАРШРУТИЗАЦИЯ

**Порядок сортировки (lexicographic, от важного к неважному):**

1. **Зависимости:** blocked_by существует и незакрыт → задача в хвост, её блокер впереди
2. **CONFIRM отдельно:** CONFIRM-задачи собираются в отдельную очередь (батч в конце)
3. **Priority:** high → medium → low
4. **Deadline:** OVERDUE → TODAY → WEEK → LATER → NO-DEADLINE
5. **Revenue weight:** клиент-платящий > клиент-presale > продукт > внутреннее
6. **Estimated time:** короткие вперёд (≤10 мин → 10-30 → 30-60 → 60+)

**Revenue weight таблица** (из `revenue-goal.md`): клиенты с MRR 50K+ → вес 3, 20-50K → 2, <20K → 1, presale → 0.5, продукты → 0.3, внутреннее → 0.1.

**Маршрут (порядок разрешения):**

1. `skill: X` явно в задаче → **использовать X** (абсолютный приоритет)
2. `human_only: true` → маршрут `human-only` (см. ниже)
3. Проект/тег Asana → таблица скиллов
4. Эвристика по keywords в title
5. Fallback → `general-purpose` агент

**Расширенная таблица маршрутов:**

| Keywords / тег | Скилл | Агент | Категория |
|----------------|-------|-------|-----------|
| seo, позиции, ключевые, топвизор | `/seo-master` | seo-analyzer | tech |
| кп, presale, предложение, pitch | `/presale-kp` | sales-engineer | revenue |
| контент, статья, блог, текст | `/content-writer` | technical-writer | content |
| html, страница, лендинг, page | `/page-review` | frontend-developer | web |
| линкбилдинг, ссылки, pbn, дропы | `/linkbuilding` | seo-analyzer | seo |
| бот, telegram, tg, flow | `/bot-fix` | general-purpose | bot |
| аудит, проверка, review | `/code-audit` | code-reviewer | qa |
| schema, json-ld, микроразметка | `/schema-markup` | seo-analyzer | seo |
| geo, ai видимость, aivision | `/geo-audit` | seo-analyzer | seo |
| ppc, реклама, директ, директ-радар | `/paid-ads` | general-purpose | ads |
| cro, конверсия, а/б, ab | `/cro` | general-purpose | marketing |
| баг, crash, fix, stack trace | `/ai-fix` | debugger | bug |
| мониторинг, отчёт, дашборд | `/client-monitor` | general-purpose | ops |
| деплой, сервер, vps, nginx, pm2 | devops | devops-engineer | infra |
| дизайн, макет, figma, pencil | pencil MCP | ui-designer | design |
| **финансы, пролив, перевод, счёт, акт** | `/finance-ops` | general-purpose | **finance** |
| **встреча, звонок, переговоры, meeting** | `/meeting-prep` | general-purpose | **human** |
| **hr, вакансия, найм, увольнение** | `/hr-vacancy` | general-purpose | **hr** |
| **ндс, налоги, бухгалтерия, декларация** | `/accounting-prep` | general-purpose | **accounting** |
| **договор, нда, акт, контракт** | `/legal-doc` | technical-writer | **legal** |
| **e2e, playwright, browser test** | `/e2e-bot-testing` | e2e-runner | test |
| **скриншот, визуал, ui ревью** | `/ui-review` | ui-visual-validator | visual |

**Маршрут `human-only`** — не вызывает агента-исполнителя. Вместо этого:
1. Подготавливает материалы (brief, ссылки, последние цифры)
2. Формирует сообщение в TG ответственному (Антон/Андрей/Стас) через CONFIRM-батч
3. Задача в Asana помечается `@waiting_human` (story, не completion)
4. В отчёт — секция "Ожидает человека"

→ Результат: у каждой задачи `skill`, `agent`, `priority`, `wave_group`. СРАЗУ ФАЗА 3.

### ФАЗА 3: ВЫПОЛНЕНИЕ (волнами)

**Критерии независимости (можно параллелить):**
- Разные `client`/`product` ИЛИ
- Разные файлы/директории (нет пересечения путей) ИЛИ
- Разные репо (`session`)

**НЕ параллелить:**
- Две задачи на один файл (проверка по заявленным путям в task notes)
- Зависимые (`blocked_by`)
- Задачи одного клиента с пересечением git paths
- CONFIRM-задачи (всегда в батч, не в wave)

**File-lock:** перед стартом агента — взять lock `clients/<c>/.combine-lock` (flock). Освободить после git commit.

**Wave-политика:**
- Макс 3 агента параллельно (токены)
- Макс 5 задач в одной волне
- Если 4+ независимых → wave_1 запускается, остальные ждут завершения любого агента → добор

**Таймаут по категории задачи:**

| `estimated_minutes` | Категория | Hard timeout |
|---------------------|-----------|--------------|
| ≤10 | quick | 10 мин |
| 10-30 | normal | 30 мин |
| 30-60 | medium | 60 мин |
| 60-180 | big | 180 мин |
| >180 | epic | split на подзадачи перед запуском |

По умолчанию (`null`) → normal (30 мин).

**Стандартный промпт агента (шаблон):**
```
CONTEXT:
  session: <session>
  cwd: <абсолютный путь по session>
  client: <name или -->
  product: <name или -->
  files to read first:
    - clients/<c>/CLAUDE.md (rules)
    - clients/<c>/context-log.md (tail -50)
    - clients/<c>/patches/ (все .md)
  brand/CMS/bans: <из CLAUDE.md клиента>

TASK:
  <title>
  notes: <Asana.notes или TODO-контекст>
  priority: <high/medium/low>
  deadline: <due или -->

SUCCESS CRITERIA:
  result_type: <code|html|doc|deploy|asana-only>
  что считается готовым: <конкретный deliverable>

CONSTRAINTS:
  - НЕ править код на VPS (git only)
  - Factcheck ПЕРЕД scp
  - Не писать AI/нейросети в публичных материалах
  - Русский язык

RETURN:
  - List файлов изменённых
  - Результат проверок (если запускал)
  - Команды для публикации (scp/git push/etc)
```

После работы агента — СРАЗУ фаза 4 для ЭТОЙ задачи (не ждать остальных).

### ФАЗА 4: ПРОВЕРКА

**4a. По типу результата:**

| `result_type` | Проверки (в порядке) |
|---------------|---------------------|
| `html` | factcheck-v2 (URL + числа) → DOM-валидация → screenshot 3 bp → ui-visual-validator |
| `doc` | factcheck (числа через senior-агент) → screenshot |
| `code` | `run-tests.sh` → lint → build (если нужен) |
| `deploy` | syntax check → dry-run |
| `deploy-bot` | 4a + pre-deploy healthcheck план |
| `asana-only` | пропуск |
| `human` | пропуск (но готовится brief) |

**4b. Factcheck URL (обязательно для html/doc):**
```bash
python3 ~/artvision-data/scripts/factcheck-v2.py --standard <file>
```
- CRITICAL > 0 → autofix через Edit → повторный factcheck (макс 2 попытки) → 3+ фейл = skip задача
- WARNING → в context-log, продолжить
- PASS → дальше

**4c. Factcheck чисел (senior-агент):**

Для КП / отчётов клиенту / документов с цифрами:
```
Agent(code-reviewer): "Проверь числа в <file> перекрёстно. Каждое число — источник?
URL живой? (curl -sI). Маркируй CONFIRMED/UNCONFIRMED/WRONG."
```
- WRONG → autofix или skip
- UNCONFIRMED → разрешено, но помечается в документе
- CONFIRMED → дальше

**4d. DOM-валидация (HTML):**
```bash
python3 scripts/validate_wave1_dom.py --file <name>
```
FAIL → Edit autofix → retry (макс 2). Fail → skip.

**4e. Screenshot + визуал (HTML/dashboards):**

Скриншоты на `desktop:1440`, `tablet:768`, `mobile:375`. Затем `ui-visual-validator` проверяет:

| Критерий | PASS | FAIL |
|----------|------|------|
| Белый экран / пустая страница | контент виден | пусто → skip |
| Overflow horizontal | нет | есть → autofix CSS |
| Обрезанный текст | нет | есть → autofix |
| Битые картинки (broken icons) | нет | есть → factcheck URL |
| TOC/nav видны | есть | нет → warning |
| Контраст текста | читаем | не читаем → warning |

FAIL критичных (белый экран, overflow) → autofix → retry.

**4f. Bot healthcheck (для `result_type=deploy-bot`):**

После деплоя:
```bash
# 1. pm2 status: не restart loop
pm2 jlist | jq '.[] | select(.name=="<bot>") | {restarts, uptime, status}'

# 2. Логи за последние 2 мин: нет ERROR/Exception
pm2 logs <bot> --lines 100 --nostream | grep -iE "error|exception|traceback"

# 3. Healthcheck endpoint (если есть):
curl -sf https://<bot>.artvision.pro/health || exit 1

# 4. Smoke test через API:
python3 scripts/bot-smoke-test.py <bot>
```

Любой FAIL → rollback (см. ФАЗА 5d).

**4g. Post-publish curl (обязательно для HTML на VPS):**

После scp:
```bash
# Все <a href>, <img src>, <link href> из HTML → curl -sI
python3 ~/.claude/scripts/post-deploy-curl.py <url>
```
5+ 404/500 → rollback.

→ Все проверки PASS → СРАЗУ ФАЗА 5.
→ 2 цикла autofix → skip, записать ошибку в `patches/`.

### ФАЗА 5: ПУБЛИКАЦИЯ

**5a. Матрица публикаций:**

| Тип | Действие | Уровень | Post-check |
|-----|----------|---------|-----------|
| Git push | `git push` | 🟢 AUTO | - |
| Файл на VPS | `scp` + restart | 🟢 AUTO | curl (4g) |
| WordPress draft | REST API draft | 🟢 AUTO | - |
| WordPress publish | REST API publish | 🔴 CONFIRM | - |
| MODX/Bitrix publish | Playwright | 🔴 CONFIRM | - |
| Деплой бота | git push → pm2 | 🟢 AUTO | healthcheck (4f) |
| Отправка TG клиенту | - | 🔴 CONFIRM | - |
| Отправка email клиенту | - | 🔴 CONFIRM | - |
| Напоминание команде | TG group | 🟢 AUTO | - |
| Asana комментарий | `create_task_story` | 🟢 AUTO | - |

**5b. AUTO — без остановки.** Выполняется сразу после проверок.

**5c. CONFIRM — единый батч в конце прогона:**

```
═══════════════════════════════════════════
  CONFIRM — нужно подтверждение (1 раз)
═══════════════════════════════════════════
  [1] WP publish: "SEO-статья BluMart" → artvision.pro/blog/...
  [2] MODX publish: "Страница НДС" → ant.partners/nds/
  [3] TG клиенту Mirulidi: "Отчёт за март"
  [4] Meeting brief для Антона: Бабуров 15.04 — документ готов
═══════════════════════════════════════════
  "го все" / "1,3" / "стоп"
═══════════════════════════════════════════
```

**CONFIRM-таймаут:**
- Батч показан → если нет ответа 30 мин → TG-уведомление Антону с номерами
- 3 часа нет ответа → задачи помечаются `[waiting-confirm]`, откладываются до следующего прогона
- Блокирует только эти задачи, остальные AUTO уже выполнены

**Зависимые от CONFIRM:** задача B с `blocked_by: A` где A — CONFIRM → B идёт в батч тем же блоком («сначала A, потом B»), помечается `blocked-by-confirm`.

**5d. Rollback (если post-check fail):**

| Тип | Rollback |
|-----|----------|
| Git push | `git revert HEAD` + push |
| scp HTML | `scp <file>.bak <server>` (backup создаётся ПЕРЕД scp автоматически) |
| Деплой бота | `pm2 stop` → `git reset --hard HEAD~1` → `pm2 restart` → healthcheck |
| WP draft | `DELETE /wp/v2/posts/<id>` |
| WP publish | `PATCH status=draft` |

Rollback успешен → задача в отчёт как `⚠️ ROLLED BACK`, в patches/ клиента запись. Rollback фейл → алерт в TG немедленно.

### ФАЗА 6: ЗАКРЫТИЕ

**6a. Asana:**
```
asana_update_task(task_id=<gid>, completed=true)
asana_create_task_story(task_id=<gid>,
  text="✅ <дата>. Результат: <deliverable>. Проверено: <factcheck/healthcheck/visual>. Публикация: <url/git>")
```

Если задача была только в TODO (не в Asana) → создать задачу в Asana как `completed:true` (зеркало).

**6b. TODO.md:**
`- [ ] задача` → `- [x] задача (✅ <дата>)`. В конце файла — блок `## Завершено <дата>` с перемещёнными строками.

Задача только в Asana → добавить строку `- [x]` в соответствующий TODO (зеркало).

**6c. context-log.md клиента:**
```markdown
## <дата> — combine
- Задача: <title>
- Скилл: <skill>
- Проверки: <список>
- Публикация: <url/git sha>
- Время: <минут>
```

**6d. patches/ клиента (если были ошибки autofix):**
```markdown
## <дата> — <тип ошибки>
- Задача: <title>
- Что сломалось: <описание>
- Как пофиксили: <fix>
- Урок: <что добавить в CLAUDE.md>
```

**6e. git commit + push:**
```
chore(combine): <дата> — <N> задач
- <client1>: <titles>
- <client2>: <titles>
```
Один commit на прогон (не на задачу) — экономит историю.

→ Следующая задача. Без паузы.

---

## ОТЧЁТ (1 раз в конце прогона)

**Куда:** stdout + TG group (чат команды, `team-chat`) + файл `reports/combine-<YYYY-MM-DD-HH>.md`.

**Шаблон:**
```
═══════════════════════════════════════════════════════
  КОМБАЙН — <дата> <HH:MM> — <длительность>
═══════════════════════════════════════════════════════

✅ Выполнено + опубликовано: <N>
  1. [<client>] <title> → <skill> → verify ✅ → <publish_target> → Asana ✅
  2. ...

⏸️ CONFIRM ждёт (батч показан): <M>
  3. [<client>] <title> → готово, <publish_target>

⚠️ ROLLED BACK: <K>
  4. [<client>] <title> → <reason> → <rollback_target>

❌ SKIPPED после autofix retry: <L>
  5. [<client>] <title> → <error>

👤 HUMAN-ONLY (ждут Антона/Андрея): <P>
  6. [<client>] <title> → brief готов

📊 Агентов запущено: <X> | Revenue impact: ~<SUM> RUB
📉 Ошибок: <E> | Rollbacks: <R> | Timeouts: <T>
═══════════════════════════════════════════════════════
```

---

## ЗАЩИТА ОТ ЗАЦИКЛИВАНИЯ

- Макс 2 попытки autofix на задачу → skip + patches/
- Макс 3 параллельных агента
- Таймаут по категории (quick/normal/medium/big/epic)
- Одинаковая ошибка 3 раза подряд на разных задачах → СТОП прогон, алерт
- 5+ rollback за прогон → СТОП, проверка инфры

---

## САМОСОВЕРШЕНСТВОВАНИЕ (асинхронно, не блокирует)

После отчёта — фоновый анализ (не пауза):

| Находка | Действие | Уровень |
|---------|----------|---------|
| Паттерн ошибок на клиенте | дописать в `clients/<c>/patches/` | 🟢 AUTO |
| Новый keyword-маршрут (часто fallback) | предложить в отчёте, не править | 🟡 показать |
| Изменение rules/ или skills/ | в отчёте секция «ПРЕДЛОЖЕНИЯ» | 🔴 CONFIRM |
| Повторный factcheck fail одного URL | добавить в `skip-urls.txt` клиента | 🟢 AUTO |

Предложения идут в отчёт, не прерывают конвейер.

---

## 2 АККАУНТА — ПАРАЛЛЕЛЬНЫЙ ДИСПЕТЧ (justtrance локально + adw на VPS)

> Реальная параллель: независимые проекты/клиенты молотятся одновременно на ДВУХ аккаунтах
> (2× пул лимитов токенов). Локальный = justtrance, VPS = adw.artvision.pro (юзер `andrey`, non-root → auto-mode).
> Координация — через git (disjoint paths → нет конфликтов). См. `~/.claude/rules/vps-parallel-combine.md`.

### Когда диспетчить на VPS (авто-триггер в ФАЗЕ 2)

После сортировки очереди — если выполняется ВСЁ из:
- ≥ 4 ready-задач в очереди
- ≥ 2 **непересекающихся** группы по `client`/`product` (разные папки → нет общих файлов)
- задачи в группе-кандидате **автономны** (`confirm_level: auto`, не `human_only`, не CONFIRM по security.md)

→ разбить очередь на 2 disjoint-партиции:
- **LOCAL** (этот аккаунт) — группа с бОльшим revenue-приоритетом / где нужен мой live-контроль
- **REMOTE** (VPS adw) — disjoint-группа других клиентов

### Как отправить (примитив)

```bash
# Отправить партицию на VPS-аккаунт (возврат мгновенный, крутится в фоне):
~/.claude/scripts/combine-vps-dispatch.sh --combine "client:burenie-skv OR client:geely-a2auto"

# Проверить статус:
~/.claude/scripts/combine-vps-status.sh           # все combine-сессии
~/.claude/scripts/combine-vps-status.sh combine-<ts>

# Забрать результаты в локальный репо (git pull):
~/.claude/scripts/combine-vps-collect.sh
```

### Правила безопасности диспетча

| Правило | Почему |
|---------|--------|
| Партиции **не пересекаются по файлам** (разные `clients/<X>/`) | иначе merge-конфликт git между аккаунтами |
| CONFIRM-задачи (security.md) **остаются LOCAL** | VPS не должен сам слать клиентам / платить / деплоить prod |
| VPS коммитит+пушит после КАЖДОЙ задачи | минимизирует окно конфликта |
| Перед стартом обе стороны `git pull` (core.symlinks=false) | в origin есть битый симлинк `.claude/rules-global/core.md` |
| Локальный комбайн НЕ ждёт VPS | параллель, не блокировка; результаты собираются в конце через collect |

### Поток

```
ФАЗА 2 (сортировка) → партиция LOCAL | REMOTE
                          │            │
        LOCAL /combine ───┘            └─── combine-vps-dispatch.sh → VPS adw (tmux, headless, auto)
        (этот аккаунт)                       крутится автономно, коммит+пуш по задачам
                          │                              │
                          └──── ФАЗА 6 ←── combine-vps-collect.sh (git pull результатов VPS)
                                ЗАКРЫТИЕ: отчёт по ОБЕИМ партициям
```

### Однократная настройка VPS (см. `~/.claude/rules/vps-parallel-combine.md`)

1. andrey-юзер авторизован на adw.artvision.pro: `ssh vps-andrey` → `claude` → `/login` → код
2. andrey-репо на `feat/ops-crm-v1`, `core.symlinks=false`, SSH git-auth (ключ скопирован)
3. `--dangerously-skip-permissions` работает (non-root)

---

## АВТОРЕЖИМ (cron)

**`комбайн авто`** — настраивает два LaunchAgent:

```
09:30 — morning run:
  - git pull всех репо
  - combine без CONFIRM-пауз (все CONFIRM → батч в TG 10:00)
  - отчёт в TG группу

18:00 — evening run:
  - combine ревью дня
  - самосовершенствование
  - предложения → TG Антону
```

Скрипты: `~/.claude/scripts/combine-auto-morning.sh`, `combine-auto-evening.sh`.
Логи: `~/Library/Logs/combine-auto.log`.
