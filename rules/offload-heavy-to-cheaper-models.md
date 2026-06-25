# Тяжёлое чтение/анализ → НЕ Claude-квота, а Codex/Gemini/round_table (DEFAULT ON)

> Установлено 2026-06-25 (Антон). Пока активен баг трат токенов Claude Code (cache-invalidation 10-20×, GH #41930/#46917/#65687 — см. `TOKEN-LEAK-CONSOLIDATED.md`) — беречь недельный Max-лимит: уводить тяжёлую механику на ДРУГОЙ биллинг.
> Связано: `consilium-matrix.md` (составы), `orchestration-method-selection.md`, `cost-aware-alternatives-first.md`, `offload-to-script-on-high-spend.md`, `codex-dev-lifecycle.md`.

## Правило (применять САМ, без напоминания)
Задача = тяжёлое чтение/анализ/ресёрч БЕЗ нужды в нашем приватном контексте (правила/клиенты/секреты) → увести с Claude-квоты:

| Триггер задачи | Куда | Биллинг |
|---|---|---|
| Разбор логов/данных, замеры, аудит больших файлов, статистика | **Codex** (`/codex` / subagent `codex:codex-rescue`) | OpenAI (не Claude) |
| Консилиум / факт-чек / второе мнение / приоритизация / сравнение | **round_table** (`mcp__llm-consilium__round_table`, Groq) | FREE |
| Большой контекст/репо, frontend-мультимодал (Figma→код), 1M ctx | **Gemini** (`gemini-rescue`) | FREE OAuth |
| Тяжёлый механический парсинг/сборка (повторяемое) | скрипт/генератор (`offload-to-script-on-high-spend`) | 0 LLM |
| Веб-ресёрч многими fetch | Codex ИЛИ один Sonnet-субагент (не рой Opus) | — |

## Остаётся в Claude Code (НЕ уводить)
Интерактив с Антоном · клиентские артефакты (КП/страницы/аудиты — нужны наши правила/бренд/контекст) · CONFIRM-операции · короткие правки.

## Гигиена Claude-квоты (при любой работе в CC)
- Новая задача → `/clear` или новая сессия. НЕ resume раздутую (resume ломает кэш → 10-20×).
- Не оставлять idle >5 мин (TTL кэша 5 мин → пересборка по полной).
- Большой tool-результат (API/Lighthouse/SEMrush) → в файл, в чат сводка.
- Рутина — обычный Opus 4.8 (200K), 1M-вариант только когда реально нужно огромное окно.

## Антипаттерны
- ❌ Гнать тяжёлый разбор логов/данных в Claude Code, когда Codex сделает без траты Max-квоты.
- ❌ Рой Opus-субагентов на ресёрч (каждый = +дамп правил ~110K, full-price под cache-багом).
- ❌ Уводить на Codex/Gemini клиентский артефакт (теряется наш контекст/правила/бренд).

## Sync / enforcement
`~/.claude/rules/` → 3 аккаунта. Кандидат-хук (TBD, approve): `prompt-offload-heavy-detect.sh` (UserPromptSubmit, inject-only) — на «разбери логи/проанализируй данные/аудит файла/замерь» нудж «увести на Codex/round_table». Bypass `OFFLOAD_HEAVY_OFF=1`. Не регистрировать без approve + тест.
