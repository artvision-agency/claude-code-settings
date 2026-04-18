---
name: process-link
description: Обработать одну или несколько pending-ссылок из таблицы link_inbox. Fetch → факт-чек → flashcard → memory → edit TG-сообщение. Вызывается из link-processor.sh.
disable-model-invocation: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
  - WebSearch
---

# process-link — превратить URL в карточку знаний

## Когда использовать
Тебя запустил `~/.claude/scripts/link-processor.sh` (LaunchAgent `pro.artvision.link-processor`). Задача: обработать **1-5 pending** строк из `link_inbox` (Supabase). После этого скрипт сам выйдет.

## Жёсткий контракт

Работаешь **автономно, без вопросов**. Каждый pending URL должен за этот прогон стать **либо `processed`, либо `failed`**.

Шаги строго по порядку:

### 1. Достать pending-строки

```bash
python3 ~/.claude/scripts/link-inbox-query.py --pending --limit 5
```

JSON с полями: `id, user_id, chat_id, temp_message_id, url, platform, created_at`.

Если пусто — завершить без работы.

### 2. Для каждой строки: status='processing'

```bash
python3 ~/.claude/scripts/link-inbox-query.py --mark-processing <id>
```

### 3. Fetch контент

**Порядок попыток:**
1. `WebFetch` с промптом "Extract: author, title, full text content, 3-5 key claims with numbers/dates. 200 words max."
2. Если fail (402/блок) → `curl -s "https://r.jina.ai/<URL>"` (Jina Reader, работает для IG/X/Medium/VC)
3. Для YouTube — `WebFetch` на youtube.com/watch?v=... возвращает заголовок + описание

Сохрани сырой контент в `raw_content` поле (через query.py).

### 4. Factcheck

Для каждого **утверждения из поста** (факт/число/дата):
- `WebSearch` с ключевой фразой, найти 2+ независимых источника
- Маркировка:
  - **CONFIRMED** — есть ≥2 независимых источника
  - **UNCONFIRMED** — только автор/один источник
  - **WRONG** — противоречит другим источникам

**Особое внимание — версии продуктов:** если пост упоминает "Claude", "GPT", "LLaMA" и т.п. — найди **текущую версию на дату fetch** (WebSearch "latest Claude model 2026"), не полагайся на training data. Сегодня Opus 4.7 + Sonnet 4.6 актуальны — но ПРОВЕРЬ перед записью.

### 5. Применимость к Artvision

Прочитай **обязательно перед классификацией:**
- `/Users/antonk/artvision-data/PROJECTS.md` (текущий обзор продуктов и клиентов)
- Последние 5 записей в `/Users/antonk/.claude/projects/-Users-antonk/memory/` с префиксом `trend_*`, `product_*`, `client_*`

Сопоставь содержимое ссылки с:
- **Продуктами:** AIvision, Direct-Radar (Scout), Card Duel, SEO Pipeline (Flow), Artssistant, ArtSync, LinkForge (PBN), Content Lab, Pulse, VoxRate, HH-Leadgen (Leads)
- **Клиентами:** Творим, BluMart, ANT Partners, Mirulidi, AdvertMed (Варикознет), OTIDO, Extru, Atribeaute, Roman Mebel, Burenie-SKV, Закваски.рус
- **Процессами команды:** автоматизация, QA, деплой, кп-генерация, factcheck pipeline

Для каждой связки — **конкретное применение ИЛИ явное "не применимо"**. Не натягивай сову на глобус: "не применимо" — валидный ответ.

### 6. Карточка (для editMessage)

Формат (HTML для Telegram, ≤ 1024 символа для каптиона, ≤ 4096 для текста):

```
📚 <b>{title}</b>
by {author} · {platform} · {date}

🎯 <b>Суть:</b> {1-2 предложения}

🔍 <b>Как работает:</b>
1. {пункт}
2. {пункт}
3. {пункт}

💡 <b>Для нас:</b>
→ {продукт/клиент}: {конкретное применение или "не применимо — почему"}
→ ...

✅ Подтверждено: {N фактов}  ⚠️ Не проверено: {M}
🔗 {url}
```

Кнопки (inline_keyboard, 3×2):
```
[📌 В задачу]  [🧠 В memory]
[🏷 Тег]       [🗑 Скип]
[🔗 Открыть]
```

callback_data: `lnk_task_{id}`, `lnk_mem_{id}`, `lnk_tag_{id}`, `lnk_skip_{id}`
Кнопка "Открыть" — `url: {url}`.

### 7. Записать в хранилища

**a) Supabase UPDATE** через `link-inbox-query.py --update <id> --json '<data>'`:
- `title, author, summary, how_it_works, applicability (JSONB), tags[], priority, confirmed_sources, raw_content, status='processed', processed_at=now()`

**b) Markdown в artvision-data** (append-mode):
Путь: `/Users/antonk/artvision-data/learning/links/{YYYY-MM}.md`
Формат (если файл есть — добавить в конец; если нет — создать с заголовком месяца):

```markdown
## {YYYY-MM-DD HH:MM} · {title}
**Source:** {url}  |  **Author:** {author}  |  **Platform:** {platform}

### Суть
{summary}

### Как работает
{how_it_works}

### Применимость
{applicability в форме списка}

### Факты (после факт-чека)
- **CONFIRMED:** {...} [src: url1, url2]
- **UNCONFIRMED:** {...}
- **WRONG:** {...}

### Теги
{tags}

---
```

**c) Memory (только если durable knowledge):**

Критерий «durable»: факт/инструмент/паттерн применим **дольше 6 месяцев** и/или меняет подход в 2+ сценариях работы. Разовые новости/хайп **не** в memory.

Если durable → `/Users/antonk/.claude/projects/-Users-antonk/memory/trend_{slug}.md`:

```markdown
---
name: trend_{slug}
description: {one-line summary, ≤150 chars}
type: reference
source: {url}
fetched: {ISO datetime}
fetched_via: {WebFetch|Jina}
author: {@handle}
confirmed_by: [{url1}, {url2}]
---

## Факт
{1-3 предложения сути}

## Применимость
- {продукт/клиент}: {как применить}

## Проверено
{дата + источники}
```

И строкой в `MEMORY.md` — под соответствующей категорией, формат `- [Title](trend_{slug}.md) — one-liner`.

### 8. Отправить карточку в TG

```bash
python3 ~/.claude/scripts/link-inbox-query.py --send-card <id>
```

Скрипт возьмёт `temp_message_id` и вызовет `editMessageText` с карточкой из DB.
Если `temp_message_id` нет — `sendMessage` новым.

### 9. Спец-кейсы

- **Ошибка fetch** (оба метода упали) → status='failed', error_message, отправить в TG: «⚠️ Не смог достать {url}. Скинь краткое описание сам — добавлю в memory.»
- **Дубликат** (процессор уже отметил) → ничего не делай, скрипт фильтрует.
- **priority='asana-pending'** (юзер нажал 📌 после обработки) → создать задачу через `python3 ~/.claude/scripts/asana-create-task.py --title "..." --notes "..."` (если скрипта нет — записать в `/Users/antonk/artvision-data/TODO.md` секция `## Из линк-инбокса` с форматом ready-задачи).
- **tags=['force-memory']** → форсим запись в memory игнорируя durable-критерий.

### 10. Лог

В `/Users/antonk/.claude/logs/link-processor-{YYYY-MM-DD}.log` одной строкой на каждую обработанную ссылку:
```
{ISO datetime} | {id:8} | {status} | {platform} | {tags joined} | {url}
```

## Принципы (не нарушать)

1. **Freshness over training data** — всегда проверяй актуальную версию продукта/инструмента через WebSearch перед записью в memory.
2. **Factcheck обязателен** — ни одно число/утверждение из поста не идёт в карточку без маркировки CONFIRMED/UNCONFIRMED/WRONG.
3. **Applicability честно** — "не применимо" лучше натянутого применения.
4. **Memory не флуд** — 1 durable факт = 1 файл. Разовые новости → только в `artvision-data/learning/`.
5. **Молча и быстро** — никаких вопросов юзеру, никаких планов. Отработал → вышел.
