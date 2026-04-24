# Handover: Путь проверки клиента + починка llm-consilium + консилиум-матрица

**Дата:** 2026-04-24 21:00
**Контекст:** ops (cwd=/Users/antonk)
**Сессия:** без имени, substantive (~90% context)
**Статус:** в работе — client-status-check Вариант B ждёт утверждения

## 🎯 Цель сессии

Ответить «что по Есениной, что просрочено» → формализовать путь проверки клиента как правило → валидировать подход сообществом → параллельно починить llm-consilium (kimi-k2 падал) → добавить Codex в матрицу консилиумов.

## ✅ Что сделано

- **Ответ по Есениной:** КП v9 задеплоен 23.03, клиент недовольна («Вы издеваетесь?»), план просрочен на 47 дней (оригинальный deadline 08.03.2026). Детали в предыдущем ответе.
- **`~/.claude/rules/consilium-matrix.md`** — новое правило, 4 слота консилиумов:
  1. `/cons` — Claude-рой по клиенту (`clients/<slug>/`)
  2. `mcp__llm-consilium__round_table` — open-source LLM (Groq FREE + OR paid)
  3. `Agent` tool с `run_in_background:true` — Claude-субагенты, параллельный ресерч
  4. `codex:codex-rescue` — GPT-5.4 OpenAI closed через Codex CLI v0.118.0
- **`~/.claude/mcp-servers/llm-consilium/server.py`** починен:
  - `MASTER_MODEL="gpt-oss-groq"` (раньше kimi-k2 — снят с Groq 04.2026)
  - Default round_table models: `"llama,qwen3,gpt-oss-groq"` (3 семейства FREE)
  - Kimi-k2 перенесён на OpenRouter (`moonshotai/kimi-k2-thinking`)
  - Добавлены `kimi-k2-latest`, `deepseek-r1`, `deepseek-v4-pro`, `deepseek-v4-flash` — upgrade-path
- Синтаксис проверен (`ast.parse` OK), тест round_table прошёл в текущей сессии с явными моделями.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| `MASTER_MODEL="gpt-oss-groq"` (120B) | deepseek-r1, kimi-k2-thinking | Groq FREE, работает сейчас. Платные — баланс 0 |
| Default round_table = llama+qwen3+gpt-oss-groq | llama+kimi-k2+qwen3 (старое) | Kimi-k2 снят с Groq, 3 семейства (Meta/Alibaba/OpenAI gpt-oss) |
| Консилиум-матрица как **правило**, не slash-команда | `/consilium-choose` команда | Правило загружается в каждую сессию, срабатывает на триггеры неявно |
| Codex = 4-й отдельный слот | Добавить в round_table | Codex CLI видит полный репо-контекст, не только промпт. Closed OpenAI — другой bias от open-source |
| Путь проверки клиента через **детерминированный bash** (CCPM-паттерн) | LLM-поиск через 10 Read | Экономит контекст ×5, CCPM (6k stars) подтвердил эффективность |
| Проверка через round_table перед фиксацией пути | Доверять только своему опыту | Правило `tool-adoption-proof.md` обязывает независимое мнение |

## ❌ Что НЕ сделано

- **`client-status-check.md` Вариант B** — 4 артефакта ждут утверждения:
  1. `~/.claude/rules/client-status-check.md` — правило (драфт есть в транскрипте)
  2. `~/artvision-data/scripts/client-status.sh` — bash-сборщик
  3. `/client-status <slug>` — slash-команда
  4. `clients/<slug>/status.jsonl` — append-only лог
  Пользователь сказал «да» на `consilium-matrix.md`, НЕ на Вариант B. Нужно переспросить явно.
- **MCP-процессы не перезапущены** — 13 штук в памяти, старые. Новые дефолты подхватятся:
  - При новой сессии Claude автоматически
  - Или вручную: `pkill -f llm-consilium/server.py`
- **Баланс OpenRouter + DeepSeek direct = 0** — Kimi и DeepSeek-R1 не работают до пополнения ($5 OR / $2-5 DeepSeek)

## 📚 Уроки (новое знание)

- **Kimi-k2-instruct снят с Groq** (обнаружено 2026-04-24). Live Groq models: llama-3.3-70b, qwen3-32b, openai/gpt-oss-120b, openai/gpt-oss-20b, llama-4-scout. Kimi теперь только через OpenRouter.
- **gpt-oss-120b (Groq FREE)** = достойный мастер-синтезатор. Заменяет DeepSeek-R1 когда нет баланса.
- **Разные слои консилиумов не дублируют**: `/cons` = клиент+стратегия, `round_table` = второе мнение на решение, Agent-рой = параллельный ресерч, `codex-rescue` = rescue кода. Правило фиксирует это.
- **CCPM-паттерн** (community validated): status-отчёт через bash-скрипт, не через LLM-рассуждение. Natural-language триггер → shell команда → LLM только синтезирует вывод.
- **Progressive disclosure** (Agent-Skills-for-Context-Engineering, 10k stars): summary первым, детали on-demand. Применить к client-status.
- **До пополнения балансов — стек 3 FREE моделей достаточен** для валидации большинства решений. Kimi/R1 — nice-to-have для сложного reasoning.

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** Спросить Антона прямо: «Утверждаем Вариант B client-status-check? Да/нет/корректировки» → если да, делать 4 артефакта
2. **HIGH:** Прогнать новый `client-status.sh` на Есениной и сравнить вывод с тем что дал руками (validation)
3. **MEDIUM:** Перезапустить MCP-процессы llm-consilium чтобы новые дефолты подхватились: `pkill -f llm-consilium/server.py` (13 процессов завершатся, Claude Code автоматом рестартанёт при следующем вызове)
4. **MEDIUM:** Предложить Антону пополнить OpenRouter ($5) или DeepSeek ($2-5) для доступа к Kimi + DeepSeek-R1 — полный 5-модельный стек
5. **LOW:** Актуализировать TODO по Есениной — задачи от 13.04 висят 11 дней, клиент молчит с 24.03 (месяц)

## 🗺️ Карта файлов

```
~/.claude/rules/
├── consilium-matrix.md            ← СОЗДАН в этой сессии
├── tool-adoption-proof.md         ← обязывает round_table перед adoption
├── parallel-tasks.md              ← триггер Agent-рой
└── client-status-check.md         ← НЕ создан, драфт в транскрипте

~/.claude/mcp-servers/llm-consilium/
└── server.py                      ← ОБНОВЛЁН (MASTER, default models, upgrade-path)

~/artvision-data/
├── clients/esenina/               ← клиент на котором тестировали путь проверки
│   ├── CLAUDE.md
│   ├── context-log.md
│   ├── config.yaml
│   ├── DELIVERABLES.md
│   ├── kp/index-v9.html           ← актуальная версия КП
│   ├── patches/corrections-log-2026-03-23.md
│   └── tz-from-tg-chat.md
└── projects/esenina/PLAN_v2.md    ← таймлайн, просрочен на 47 дней
```

## ⚠️ Gotchas

- **13 MCP-процессов llm-consilium в памяти** — правки server.py НЕ подхвачены в текущих процессах. Новая сессия Claude получит актуальный код автоматически.
- **Баланс OpenRouter = 0 / DeepSeek direct = 0** — любой вызов с `master="kimi-k2"` или `master="deepseek-r1"` вернёт 402. Оставаться на Groq FREE до пополнения.
- **Context был 90%+** на момент handover — следующая сессия с /clear, поднять ОТ ЭТОГО файла.
- **Пользователь спросил «/cons раньше вызывался авто?»** — честный ответ: НЕТ, только по явному триггеру. Новая матрица формализует авто-вызов. Если хочет консервативно — скажет в следующей сессии.
- **Есенина молчит с 24.03** (месяц). 15K остаток оплаты под риском. Предложение клиента «приехать лично собрать» висит без ответа от нашей стороны.
- **Правило no-smoothing** — честно признавать что работает / не работает. В прошлом ответе признал «не применял Managed Agents, только round_table» — пользователь оценил.

## 🔗 Связанные ресурсы

- Правило: `~/.claude/rules/tool-adoption-proof.md` (обязывает round_table)
- CCPM паттерн: https://github.com/automazeio/ccpm
- Agent-Skills-for-Context-Engineering: https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering
- pro-workflow (self-correcting memory): https://github.com/rohitg00/pro-workflow
- llm-consilium код: `/Users/antonk/.claude/mcp-servers/llm-consilium/server.py`
- Codex CLI: `/Users/antonk/.local/npm-global/bin/codex` v0.118.0
