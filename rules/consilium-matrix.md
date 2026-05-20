# Консилиум-матрица: `/cons` vs `round_table` vs Agent-рой vs Codex vs Gemini

> Пять инструментов на пяти слоях (четыре семейства LLM: Claude, OpenAI closed, Google closed, open-source).
> Этот файл решает **что вызывать когда**, чтобы не путать и не дублировать.

## Быстрый выбор (смотри сюда первым)

| Сигнал в запросе | Инструмент | Слой |
|---|---|---|
| «разбери клиента X», «стратсессия», «что делать с Y», «конкуренты», «cons», «консилиум» | **`/cons`** (skill) | Claude-рой по клиенту |
| «проверь моё решение», «дай второе мнение», «что думают другие», внедрение нового инструмента/паттерна, tool adoption | **`mcp__llm-consilium__round_table`** | Внешние open-source модели (Groq/OR) |
| «параллельно исследуй», «3 агента в worktree», глубокий ресерч репо/темы | **Agent tool, `run_in_background: true`** | Claude-субагенты |
| «Claude застрял», «дай другой взгляд на код», «второй pass реализации», rescue сложной архитектуры, backend/системная диагностика | **`codex:codex-rescue`** (subagent_type) | GPT-5.4 OpenAI closed-flagship |
| «UI/frontend handoff», «Figma → код», «mockup», «большой UI-проект», «дай Google-pov», «1M контекст репо» | **`gemini-rescue`** (subagent_type) | Gemini 2.5 Pro Google closed-flagship |
| Кросс-валидация критичного решения | **несколько подряд** | See «Совмещение» |

## Различия по природе

|  | `/cons` | `round_table` | Agent-рой | `codex:codex-rescue` | `gemini-rescue` |
|---|---|---|---|---|---|
| **Что** | Slash-skill, рой senior-Claude-субагентов | MCP-tool, внешние LLM через API | `Agent` tool, параллельные Claude-сессии | Handoff на OpenAI Codex CLI через shared runtime | Handoff на Google Gemini CLI через bash wrapper |
| **Модели** | Claude Opus × N ролей | llama + qwen3 + gpt-oss-120b (FREE Groq) + kimi-k2/deepseek-r1 (если OR оплачен) | Claude Opus/Sonnet | **GPT-5.4 (closed flagship OpenAI)** | **Gemini 2.5 Pro / 3.1 Pro Preview (closed flagship Google)** |
| **Вход** | `clients/<slug>/` — research, data, competitors | Произвольный промпт | Произвольный промпт + список файлов | Полный репо-контекст через Codex CLI | Промпт + опционально файлы (1-2M ctx) + картинки (`--image`) |
| **Выход** | HTML-дашборд/MD, action items с ROI | Тексты 3+ моделей + взвешенный синтез | Summary-пакет от каждого агента | Diagnosis/patch/second implementation | Frontend код / UI mockup / second opinion |
| **Стоимость** | Claude Max (~$0.5–2) | **FREE** (Groq) или $5 OR за Kimi/R1 | Claude Max (~$0.10–0.50 на агента) | Codex subscription / API credits | **FREE 60 RPM** через OAuth Code Assist ИЛИ API key с billing |
| **Bias** | Одно семейство (Claude) | **Независимое** — ловит Claude-bias | Одно семейство (Claude), но изоляция контекста | **OpenAI семейство** — ловит Claude-bias на коде | **Google семейство** — ловит Claude+OpenAI-bias, силён на frontend/мультимодальном |

## Когда применять

### `/cons` — клиентская стратсессия
- Есть конкретный клиент в `clients/<slug>/`
- Нужен анализ конкурентов, рынка, позиционирования
- Нужен action plan с ROI
- **НЕ использовать** для: проверки собственного решения, общих вопросов, tool adoption

### `round_table` — второй голос
- **ОБЯЗАТЕЛЬНО** перед внедрением внешнего инструмента (правило `tool-adoption-proof.md`)
- Когда решение принимается в одиночку и нужна независимая валидация
- Когда хочется поймать Claude-bias («NIH» — not-invented-here)
- Дёшево (FREE) — можно звать часто
- **НЕ использовать** для: глубокого ресерча конкретных репо (ограничен контекст промпта), вопросов про клиента (не имеет доступа к файлам)

### Agent-рой — параллельный глубокий ресерч
- 2+ независимых ресерч-задач (3 репо, 4 аспекта темы)
- Нужен доступ к Bash/WebFetch/Grep у каждого
- Нужен изолированный контекст (worktree)
- **НЕ использовать** для: быстрых вопросов, кросс-валидации (используй round_table)

### `codex:codex-rescue` — GPT-5.4 на backend/архитектуре
- Claude застрял / ходит кругами на сложной задаче
- Нужен второй pass реализации другим семейством
- Глубокая диагностика бага который Claude не может root-cause
- Backend / системная архитектура / алгоритмы / низкоуровневое
- Спорный код — спросить closed-flagship OpenAI
- **Преимущество над `round_table`**: полный репо-контекст через CLI, не просто промпт. Лучше на коде, архитектуре, bug hunting.
- **Преимущество над Agent-роем**: другое семейство → ловит Claude-bias, not-invented-here
- **НЕ использовать** для: стратегии по клиенту (нет контекста `clients/`), быстрых вопросов без кода, frontend-handoff (там Gemini сильнее)
- Скилл: `codex:codex-cli-runtime`, `codex:gpt-5-4-prompting`, `codex:codex-result-handling`

### `gemini-rescue` — Gemini 2.5 Pro на frontend/UI/мультимодальном
- Frontend-задачи: Figma → React/HTML, UI рефакторинг, mockup → код
- Мультимодальный handoff: screenshot страницы → анализ + правки
- Большое репо: 1-2M context вмещает на 5-10× больше файлов чем Claude/Codex
- Кросс-валидация архитектуры от Google (другое closed семейство, не пересекается с OpenAI/Anthropic)
- **Преимущество над `codex-rescue`**: мультимодальность нативная (картинки прямо в промпт), 1M ctx, силён на UI
- **Преимущество над `round_table`**: closed-flagship качество vs ensemble open-source
- **НЕ использовать** для: backend/алгоритмы (Codex сильнее), real-time critical (Gemini медленнее старт)
- Setup: `~/.claude/docs/gemini-setup.md` (VPN + OAuth)
- Wrapper: `~/.claude/scripts/gemini-rescue.sh`
- Запуск: `Agent({subagent_type: "gemini-rescue", prompt: "..."})`
- Модели: `gemini-2.5-flash` (быстрая, дешёвая — UI mockups) / `gemini-2.5-pro` (default, сильная) / `gemini-3.1-pro-preview` (frontier)

## Совмещение (для критичных решений)

**Каскад для клиентской стратегии (ставки >500K):**
```
1. Agent-рой (3 параллельных) — собрать данные/факты из разных источников
2. /cons — синтезировать в стратегию для клиента
3. round_table — проверить стратегию независимыми open-source моделями
```

**Каскад для критичного кода/архитектуры (backend):**
```
1. Agent-рой (3 параллельных) — собрать паттерны из community репо
2. codex-rescue — второй pass / альтернативная реализация от GPT-5.4
3. round_table — проверить финальное решение open-source моделями
```

**Каскад для frontend-проектов (UI/UX):**
```
1. Agent-рой (3 параллельных) — собрать референсы / design patterns
2. gemini-rescue — frontend implementation от Gemini (мультимодальный, 1M ctx)
3. codex-rescue — code review / safety check от GPT-5.4
4. round_table — финальная валидация (опц.)
```

Применять при: крупных presale (>500K), смене стратегии клиента, внедрении новой методологии, критичной архитектурной задаче.

**Четыре семейства в кармане:** Claude (`/cons`, Agent-рой) + open-source (`round_table`: Meta/Alibaba/OpenAI gpt-oss + Moonshot/DeepSeek) + OpenAI closed (`codex-rescue`: GPT-5.4) + Google closed (`gemini-rescue`: Gemini 2.5 Pro). Это покрывает все основные bias-векторы.

## Триггеры (автоматическое срабатывание)

`/cons` — уже срабатывает сам по `user-invocable:true` skill:
- «консилиум», «стратсессия», «cons», «разбор конкурентов», «что делать с клиентом»

`round_table` — вызываю я (Claude) по правилам:
- Перед adopt любого нового инструмента/паттерна (`tool-adoption-proof.md`)
- При явной просьбе «проверь», «дай второе мнение», «не только твой опыт»

Agent-рой — вызываю по сигналам:
- «рой», «swarm», «параллельно», «3 агента»
- Авто: 4+ независимых задач в TODO (`parallel-tasks.md`)

`codex-rescue` — вызываю по сигналам:
- «кодекс», «codex», «gpt-5-4», «gpt-5.4», «opeanai», «второе мнение на код», «rescue»
- Авто (агент `codex:codex-rescue` description): Claude застрял на задаче, ходит кругами, просит другой pass реализации, нужна глубокая root-cause диагностика
- Запуск: `Agent` tool с `subagent_type: "codex:codex-rescue"`

`gemini-rescue` — вызываю по сигналам:
- «gemini», «джемини», «гугл pov», «google second opinion», «frontend handoff», «figma → код», «UI mockup», «большое репо 1M ctx»
- Авто: задача frontend-heavy (UI, React, mockup) И нужен второй взгляд / больше контекста чем у Claude/Codex
- Авто: задача мультимодальная (картинка/Figma/screenshot → код)
- Запуск: `Agent` tool с `subagent_type: "gemini-rescue"`
- Pre-требование: VPN активен + OAuth настроен (см. `~/.claude/docs/gemini-setup.md`)

## Upgrade-path round_table (Kimi + DeepSeek-R1)

Сейчас работает FREE Groq-стек: `llama,qwen3,gpt-oss-groq` (3 семейства — Meta/Alibaba/OpenAI).
Мастер-синтезатор: `gpt-oss-groq` (120B).

При пополнении балансов автоматически доступны:
- **OpenRouter** $5 → `kimi-k2` (thinking), `kimi-k2-latest` (k2.6), `deepseek-r1` (0528)
- **DeepSeek direct** $2-5 → `deepseek-v4-pro`, `deepseek-v4-flash` (дешевле OR ×3)

Когда баланс появится — вызывать с `master="deepseek-r1"` или `master="kimi-k2"` для премиум-reasoning в синтезе.

## Параллельность и rate-limits провайдеров

> **Установлено:** 2026-05-19 (сессия 9f7e1adc, финансовый консилиум по 3M). Из 8-моделного запуска 3 OR-модели упали: qwen3-80b → HTTP 429, gemma4 → HTTP 429, hermes-405b → SSL EOF. Minimax/OR прошёл, но он попал в окно до rate-limit.

| Провайдер | Параллельность free-tier | Поведение при превышении |
|-----------|--------------------------|--------------------------|
| **Groq** | Все 4 модели параллельно — стабильно | редкие 429, бывают восстановления |
| **OpenRouter (free)** | **Максимум 2 параллельно** | HTTP 429 на 3-й модели, SSL EOF при перегрузке |
| **DeepSeek direct** | 1-2 параллельно | TBD, не тестировано на full-load |

**Правило:** для round_table из 6+ моделей — Groq всё в одном запуске, OR разбивать на 2 + 2 + 2 с задержкой 60-90 сек между группами. Если запустить 4+ OR-моделей одновременно → 50% упадут.

## Кого не дублировать в models=

Одна модель через два разных провайдера = **дубль голоса**, ломает принцип «разные школы»:
- `llama` (Groq) ≡ `llama-or` (OR) — обе llama-3.3-70b
- `gpt-oss-groq` (Groq) ≡ `gpt-oss` (OR) — обе gpt-oss-120b

Выбирать один (Groq быстрее, обычно стабильнее). Для round_table брать **разные семейства**, не разных провайдеров одной семьи.

## Рекомендованный состав (по типу задачи)

| Назначение | models= | master | Стоимость |
|------------|---------|--------|-----------|
| **Default** (любой ресерч) | `llama,qwen3,hermes-405b,gpt-oss-groq` (4 разные школы) | `gpt-oss-groq` | $0 |
| **Финансовые/денежные** | + `minimax,nemotron-120b` (6, OR режу на 2 группы) | `gpt-oss-groq` | $0 |
| **Кросс-валидация ставки >500K** | + `kimi-k2,deepseek-r1` | `deepseek-r1` | ~$0.05-0.10 |
| **Стратегия клиента / КП** | `hermes-405b,minimax,kimi-k2,llama` | `deepseek-r1` | ~$0.05 |
| **Контрarian-check** | + `grok-3` (когда будет ключ) | любой reasoner | $25 кредитов |

## Антипаттерны

| ❌ | ✅ |
|---|---|
| Запустить `/cons` чтобы проверить своё решение | `round_table` — он для этого |
| Запустить `round_table` «разбери клиента X» | `/cons` — у него доступ к `clients/` |
| Параллельный ресерч репо через `round_table` | Agent-рой — у него Bash/WebFetch |
| Внедрить новый инструмент без `round_table` | Нарушение `tool-adoption-proof.md` |
| Звать `round_table` на спорную архитектуру кода | `codex-rescue` (backend) или `gemini-rescue` (frontend) — видят репо, не только промпт |
| Застрял на код-задаче 3+ итерации → продолжать долбить один | `codex-rescue` (backend) / `gemini-rescue` (frontend) — другое семейство, свежий взгляд |
| Frontend handoff на `codex-rescue` | `gemini-rescue` — мультимодальность + 1M ctx сильнее на UI |
| Backend/алгоритмы на `gemini-rescue` | `codex-rescue` — GPT-5.4 объективно сильнее на низкоуровневом |
| `gemini-rescue` с дорогой `gemini-3.1-pro-preview` на UI mockup | `--model gemini-2.5-flash` (10× дешевле, того же качества) |
| Звать все пять подряд на простой вопрос | Overkill — используй один нужный |
