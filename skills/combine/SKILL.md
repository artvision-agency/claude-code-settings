---
name: combine
description: |
  Комбайн — непрерывный конвейер: ASANA → ВЫПОЛНЕНИЕ → ПРОВЕРКА → ПУБЛИКАЦИЯ → ASANA ✅
  НЕ останавливается между шагами. Единственная пауза = CONFIRM-уровень (security.md).
  Тянет из Asana → читает контекст → сортирует → выполняет → верифицирует → деплоит → закрывает.
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
ASANA → ВЫПОЛНЕНИЕ → ПРОВЕРКА → ПУБЛИКАЦИЯ → ASANA ✅
  │         │            │           │           │
  │         │            │           │           └─ update_task(completed: true)
  │         │            │           └─ git push / scp / WP REST API
  │         │            └─ validate-pages / factcheck / screenshot
  │         └─ skill по маршруту (seo-master, content-writer, etc)
  └─ search_tasks → sort → read context
```

**ГЛАВНОЕ ПРАВИЛО: НЕ ОСТАНАВЛИВАТЬСЯ.**
Конвейер идёт задача за задачей без пауз и вопросов.
Единственная причина остановки = 🔴 CONFIRM из security.md.

---

## РЕЖИМЫ

| Команда | Поведение |
|---------|-----------|
| `комбайн` / `го` | Непрерывный: pull → execute → verify → publish → close |
| `комбайн план` | Только показать план, не выполнять |
| `комбайн [клиент]` | Только задачи конкретного клиента |
| `комбайн ревью` | Только анализ последнего прогона |

---

## PIPELINE (6 фаз, без остановок)

### ФАЗА 1: PULL (Asana + TODO)

**1a. Задачи из Asana:**
```
mcp__asana__asana_search_tasks:
  workspace: 860693669973770
  completed: false
  sort_by: due_date
  opt_fields: name,due_on,projects,tags,notes,assignee
```

**1b. Задачи из TODO.md** (5 файлов по todo-routing.md):
```
artvision-data/TODO.md
artvision-tg-bot/TODO.md
devops-agent/TODO.md
artvision-data/presale/TODO.md
artvision-data/products/TODO.md
```

**1c. Сверка:** TODO ↔ Asana. Расхождения → исправить автоматически (AUTO).

**1d. Контекст КАЖДОЙ задачи:**
```bash
cat clients/[name]/CLAUDE.md          # правила
cat clients/[name]/context-log.md     # история
ls clients/[name]/patches/            # ошибки
```

→ Результат: единый отсортированный список задач с контекстом.
→ НЕ показывать план, НЕ ждать подтверждения. Сразу ФАЗА 2.

### ФАЗА 2: СОРТИРОВКА + МАРШРУТИЗАЦИЯ

**Приоритет (автоматический, без вопросов):**
1. 🔴 OVERDUE (просрочено)
2. 🟠 TODAY
3. 🟡 THIS WEEK (≤7 дней)
4. 🟢 LATER (>7 дней) — тоже выполнять, не откладывать
5. ⚪ NO DEADLINE — выполнять последними

**Вторичная сортировка:** revenue impact (клиент > продукт > внутреннее).

**Маршрут (проект/теги → скилл):**

| Проект/Тег Asana | Скилл | Тип агента |
|-----------------|-------|------------|
| SEO, позиции, ключевые | `/seo-master` | seo-analyzer |
| КП, presale, предложение | `/presale-kp` | sales-engineer |
| Контент, статья, блог | `/content-writer` | technical-writer |
| HTML, страница, лендинг | `/page-review` | frontend-developer |
| Линкбилдинг, ссылки | `/linkbuilding` | seo-analyzer |
| Бот, telegram | `/bot-fix` | general-purpose |
| Аудит, проверка | `/code-audit` | code-reviewer |
| Schema, json-ld | `/schema-markup` | seo-analyzer |
| GEO, ai видимость | `/geo-audit` | seo-analyzer |
| PPC, реклама, директ | `/paid-ads` | general-purpose |
| CRO, конверсия | `/cro` | general-purpose |
| Код, фикс, баг | `/ai-fix` | debugger |
| Мониторинг, отчёт | `/client-monitor` | general-purpose |
| Деплой, сервер, VPS | devops | devops-engineer |
| Дизайн, макет | pencil MCP | ui-designer |

**Маршрут не найден** → `general-purpose` агент. НЕ останавливаться.

→ Результат: каждая задача имеет скилл + тип агента + приоритет.
→ Сразу ФАЗА 3.

### ФАЗА 3: ВЫПОЛНЕНИЕ (волнами, параллельно)

**Wave-система:**
- 4+ независимых задач → параллельные агенты (Agent tool, max 3)
- Зависимые задачи → последовательно
- КАЖДЫЙ агент получает полный контекст проекта в промпте

**Для каждой задачи агент делает:**
1. Прочитать контекст (CLAUDE.md, patches/, context-log)
2. Вызвать скилл
3. Выполнить до результата
4. git add + commit (автоматически)
5. **→ СРАЗУ перейти к ФАЗА 4 для этой задачи**

**НЕ ждать завершения всех задач wave. Каждая задача идёт по конвейеру независимо:**
```
Задача A: EXECUTE → VERIFY → PUBLISH → CLOSE
Задача B: EXECUTE → VERIFY → PUBLISH → CLOSE  (параллельно)
Задача C:           EXECUTE → VERIFY → PUBLISH → CLOSE
```

### ФАЗА 4: ПРОВЕРКА (автоматическая, без пауз)

Сразу после выполнения, БЕЗ ожидания подтверждения:

**4a. Тип проверки по типу результата:**

| Результат | Проверка |
|-----------|----------|
| HTML-страница | `validate-pages` (DOM) + `factcheck-html.py` + screenshot |
| Код (py/js/ts) | `run-tests.sh` + lint |
| КП / документ | factcheck + screenshot 3 breakpoints |
| SEO-контент | мета-теги + уникальность + H1/H2 |
| Конфиг / деплой | `syntax check` + dry-run |
| Asana-only (комментарий, статус) | пропустить проверку |

**4b. Factcheck (для HTML/документов):**
```bash
python3 ~/artvision-data/scripts/factcheck-html.py [file]
```
- CRITICAL → СТОП для ЭТОЙ задачи, автофикс, повторить проверку
- WARNING → записать в context-log, продолжить
- PASS → продолжить

**4c. DOM-валидация (для HTML):**
```bash
python3 scripts/validate_wave1_dom.py --file [name]
```
- FAIL → автофикс через Edit tool → повторить валидацию → продолжить
- PASS → продолжить

**4d. Screenshot (для визуального контента):**
Снять скриншот на 3 breakpoints (desktop/tablet/mobile).
Визуальная проверка через ui-visual-validator агента.

→ Проверка пройдена → СРАЗУ ФАЗА 5.
→ Проверка НЕ пройдена → автофикс → повторить проверку (макс 2 попытки).
→ 2 попытки фейл → записать ошибку, пропустить задачу, продолжить остальные.

### ФАЗА 5: ПУБЛИКАЦИЯ

**5a. Определить тип публикации по задаче:**

| Тип | Действие | Уровень |
|-----|----------|---------|
| Git push | `git push` | 🟢 AUTO |
| Файл на VPS | `scp` + restart | 🟢 AUTO |
| WordPress draft | REST API (status=draft) | 🟢 AUTO |
| WordPress publish | REST API (status=publish) | 🔴 CONFIRM |
| MODX/Bitrix | Playwright MCP | 🔴 CONFIRM |
| Деплой бота | git push + pm2 restart | 🟢 AUTO + 5мин мониторинг |
| Отправка клиенту | — | 🔴 CONFIRM |

**5b. AUTO-публикация (без остановки):**
- git push → автоматически
- scp на VPS → автоматически
- WordPress draft → автоматически
- Деплой бота → автоматически + 5 мин мониторинг логов

**5c. CONFIRM-публикация (единственная пауза):**
Собрать ВСЕ CONFIRM-задачи в ОДИН батч в конце прогона.
Показать ОДИН раз, получить ОДНО подтверждение.
НЕ спрашивать по одной.

```
═══════════════════════════════════════════
  CONFIRM — нужно подтверждение (1 раз)
═══════════════════════════════════════════
  1. WP publish: "SEO-статья BlueMart" → artvision.pro/blog/...
  2. MODX publish: "Страница НДС" → ant.partners/nds/
  3. TG клиенту: "Отчёт Mirulidi за март"
═══════════════════════════════════════════
  Го всё? (или номера для выборочного)
═══════════════════════════════════════════
```

### ФАЗА 6: ЗАКРЫТИЕ (Asana + TODO)

Сразу после публикации, автоматически:

**6a. Asana:**
```
mcp__asana__asana_update_task(task_id=<gid>, completed=true)
mcp__asana__asana_create_task_story(task_id=<gid>,
  text="✅ Выполнено [дата]. Результат: [описание]. Проверено: [тип]")
```

**6b. TODO.md:**
`- [ ] задача` → `- [x] задача (выполнено [дата])`

**6c. context-log.md клиента:**
Дописать: что сделано, проверено, опубликовано.

**6d. git commit + push** (автоматически):
```
chore: combine [дата] — N задач выполнено
```

→ Задача закрыта. Следующая. Без паузы.

---

## ОТЧЁТ (в конце прогона, 1 раз)

```
═══════════════════════════════════════════════════════
  КОМБАЙН — итоги — [дата]
═══════════════════════════════════════════════════════

✅ Выполнено + опубликовано: N
  1. [Задача] → [скилл] → verify ✅ → publish ✅ → Asana ✅
  2. [Задача] → [скилл] → verify ✅ → git push → Asana ✅

⏸️ Ожидает CONFIRM: M
  3. [Задача] → готово, ждёт публикации

❌ Ошибка (после 2 попыток): K
  4. [Задача] → ошибка: [описание]

📊 Агентов: X | Revenue impact: ~XXX,XXX RUB
═══════════════════════════════════════════════════════
```

---

## ЗАЩИТА ОТ ЗАЦИКЛИВАНИЯ

- Макс 2 попытки автофикса на задачу → skip + записать ошибку
- Макс 3 параллельных агента
- Задача >10 мин → timeout, skip, следующая
- Одинаковая ошибка 3 раза → СТОП, показать проблему

---

## САМОСОВЕРШЕНСТВОВАНИЕ (тихое)

После отчёта — автоанализ:
1. Паттерны ошибок → `patches/` клиента (AUTO)
2. Новый маршрут → дописать в таблицу (AUTO)
3. Изменения в rules/ и skills/ → СПРАШИВАТЬ
4. Всё OK → ничего

---

## 2 АККАУНТА

Работает на justtrance + adw.artvision.pro.
Синхронизация через git (TODO, context-log, PROJECTS.md).

## АВТОРЕЖИМ (cron)

`комбайн авто`:
- 09:30: pull → выполнить AUTO → собрать CONFIRM → TG
- 18:00: отчёт + самосовершенствование
