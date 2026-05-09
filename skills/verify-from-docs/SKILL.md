---
name: verify-from-docs
description: Verifying technical answers against canonical docs before writing code. Use when user asks 'how to use/setup/configure X', 'best practice for Y', 'what's better A vs B' про конкретную библиотеку/API/framework. Pipeline — Context7 (live docs) → Anthropic cookbook → реальные примеры на github → синтез. Триггеры — 'как настроить', 'как использовать', 'как реализовать в [библиотеке]', 'best practice', 'лучшая практика', 'что лучше', 'official docs', 'документация по', 'verify from docs', 'docs lookup', 'как работает [API/library]'.
---

# verify-from-docs — проверка ответа по канон-докам ДО написания кода

> **Зачем:** претренинг Claude отстаёт на месяцы-годы. API библиотек меняется, deprecate, переименовывается. Ответ "из памяти" может быть рабочим в 2024-м и сломанным в 2026-м. Скилл заставляет сходить в живые доки и cookbook **перед** написанием кода.
>
> **Когда вызывать:** любой нетривиальный технический вопрос про конкретную библиотеку/API/framework. Не для общих вопросов «как работает HTTPS» или «что такое REST» — это не меняется.

## Pipeline (4 шага, в порядке)

### Шаг 1. Context7 MCP — actual docs

```
mcp__context7__resolve-library-id  → найти canonical id ("react", "fastapi", "aiogram")
mcp__context7__query-docs          → получить актуальный фрагмент доков
```

Для каких библиотек точно работает (проверено): React, Next.js, Vue, FastAPI, Django, Flask, Express, aiogram, grammy, Pydantic, SQLAlchemy, Drizzle, Prisma, Tailwind, shadcn/ui, Stripe, Anthropic SDK, OpenAI SDK.

Если Context7 не знает библиотеки → шаг 2.

### Шаг 2. Канонические источники вендора

| Вендор | Источник |
|---|---|
| Anthropic Claude API | docs.anthropic.com + github.com/anthropics/claude-cookbook |
| Anthropic Claude Code | docs.claude.com/claude-code + github.com/anthropics/skills |
| Telegram Bot API | core.telegram.org/bots/api |
| Yandex (Direct/Wordstat/Метрика/Вебмастер) | yandex.ru/dev — НЕ скрейпинг (`yandex-api.md`) |
| Timeweb Cloud | timeweb.cloud/api-docs (Swagger) |
| Stripe | stripe.com/docs/api + github.com/stripe-samples |
| MODX | docs.modx.com + community.modx.com |

WebFetch на канонический URL, без поисковика-промежуточного.

### Шаг 3. Реальные примеры на github (если шаги 1-2 неполны)

```bash
gh search code 'pattern' --language python --limit 10
gh search repos 'topic:claude-code-skills'
```

Только репо с **звёздами / последний коммит < 6 мес**. Один пример ≠ best practice — нужно 2-3 совпадающих.

Курированные списки:
- `hesreallyhim/awesome-claude-code` — для Claude Code/skills/hooks
- `awesome-mcp-servers` (несколько на github) — для MCP

### Шаг 4. Если всё равно неясно — внешний голос

```
mcp__llm-consilium__round_table  master=gpt-oss-groq  models=llama,kimi-k2,qwen3
```

Бесплатно через Groq. Ловит Claude-bias и not-invented-here. Правило `tool-adoption-proof.md`.

## Что выдать пользователю

**Не сразу код.** Сначала 3 строки:

```
[verify-from-docs]
Источник: Context7 / cookbook / github / round_table
Версия библиотеки: vX.Y (проверено на дате DD.MM.YYYY)
Соответствие запроса доке: 100% / 80% (примечание) / нужна доп.проверка
```

Потом — код.

## Когда НЕ нужен этот скилл

- Стандартный bash/git/POSIX — стабильны десятилетиями
- Внутренние скрипты Артвижн — читаешь файл, не доки
- Чисто архитектурные вопросы без конкретной библиотеки («как организовать модули»)
- Ответ уже подтверждён `man <cmd>` или `--help`

## Антипаттерны

| ❌ | ✅ |
|---|---|
| Писать код по памяти когда юзер спросил «как использовать [библиотеку]» | Сначала Context7, потом код |
| Доверять одному github-снippet'у | 2-3 совпадающих + дата свежая |
| WebSearch вместо канонических доков | Прямо в docs.* / github.com vendor |
| Stack Overflow ответ 2019-го | Канон-доки текущей версии |
| Сказать «обычно делают так» без источника | Маркировать UNVERIFIED либо сходить за источником |

## Связь с другими механизмами

- `docs-lookup` skill — простой fallback (только Context7), без cookbook/github/round_table
- `search-first` skill — research БЕЗ написания кода («что есть в community»)
- `crag-research` — для числовых утверждений с фактчеком
- `tool-adoption-proof.md` — round_table обязателен ДО внедрения нового инструмента
- Hook `prompt-verify-docs-detect.sh` (UserPromptSubmit) — детект «как X в Y» → инжект `[VERIFY-DOCS REQUIRED]`

## Прецедент

**2026-05-09 (эта сессия):** Антон спросил «есть ли датасеты с подтверждённой инфой?». Принято решение завести скилл + hook чтобы не полагаться только на pretraining.
