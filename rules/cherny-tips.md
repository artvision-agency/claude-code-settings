# Boris Cherny tips — поведенческие советы для Claude Code

> Источник: [howborisusesclaudecode.com](https://howborisusesclaudecode.com/), [Lenny's Newsletter interview](https://www.lennysnewsletter.com/p/head-of-claude-code-what-happens), [shanraisshan/claude-code-best-practice 15-tips](https://github.com/shanraisshan/claude-code-best-practice/blob/main/tips/claude-boris-15-tips-30-mar-26.md), tweets [@bcherny](https://x.com/bcherny).
>
> Boris Cherny — head of Claude Code в Anthropic.

## 1. CLAUDE.md = mistake log, не инструкция

> *"Anytime we see Claude do something incorrectly we add it to the CLAUDE.md, so Claude knows not to do it next time."*

**У нас:** `~/.claude/rules/self-corrections.md` — буквально это, ещё с расширением — повторные ошибки → детерминистичные хуки.

## 2. Verification loop = #1 фактор качества (2-3x)

> *"Probably the most important thing to get great results out of Claude Code — give Claude a way to verify its work."*

**У нас:** `qa-full.sh`, `factcheck-v2.py`, `validate-pages` skill, hook `pre-push-qa-check.sh`. **Gap:** verification loops для собственных скриптов/хуков отсутствуют — добавить тесты в `~/.claude/hooks/tests/` с run-on-commit.

## 3. `/rewind` вместо «попробуй ещё раз»

> *"Don't ignore context rot... use /rewind to eliminate pollution."*

Если первый ответ Claude плохой — **не уточнять промпт сверху**, а откатывать состояние через `/rewind`. Каждое неудачное «попробуй заново» оставляет в контексте мусор.

**Применять:** при сложных задачах когда Claude пошёл не туда — `/rewind` к точке до неверного промпта.

## 4. Auto-compact window 400K, не 200K

> *"Sets `CLAUDE_CODE_AUTO_COMPACT_WINDOW=400000` to compact before degradation zone (300-400k tokens)."*

**У нас:** установлено в `artvision-data/.claude/settings.json` (env section) — sync на 3 аккаунта через git pull.

## 5. Plan Mode + auto-accept = базовый workflow

> *"Most sessions start in Plan mode... then switches to auto-accept edits."* Shift+Tab дважды.

**Применять:** при правке >3 файлов — Plan Mode обязателен (для review плана). Иначе auto-accept без плана = blast-radius риск.

## 6. PostToolUse hook = форматтер последних 10%

> *"Claude is usually well-formatted, and the hook fixes the last 10% to avoid CI failures."*

**У нас:** `post-edit-lint.sh` ловит console.log/CDN — это validator, не formatter. **Идея:** добавить `shfmt -w` для shell-хуков (88 файлов в `~/.claude/hooks/` — разнобой неизбежен).

## 7. Slash commands для high-frequency triggers

> *"Use slash commands for every 'inner loop' workflow that you end up doing many times a day."*

**У нас:** 205 skills с триггерами, но `.claude/commands/*.md` нет. Для 5-10 высокочастотных (`/sync`, `/touch`, `/повестка`) — commands быстрее skills (без fuzzy-match overhead).

## 8. `--bare` flag для SDK (10x speedup)

> *"--bare to speed up SDK startup by up to 10x. Opt-in flag eliminates automatic searches for local files and MCPs."*

**Применять:** в `/swarm` и параллельных Agent вызовах когда MCP не нужны.

## 9. Hooks подхватываются file watcher автоматически (ИСПРАВЛЕНО 2026-05-28)

> **БЫЛО (устаревшая цитата, опровергнута справкой):** *"Hooks are loaded when Claude Code session starts. Changes to hook configuration require restarting Claude Code."*
>
> **СТАЛО (текущая официальная справка `code.claude.com/docs/en/hooks`, проверено 2026-05-28):**
> *"Direct edits to hooks in settings files are normally picked up automatically by the file watcher."*

**Применять:**
- После правки `settings.json` или нового хука — **рестарт НЕ обязателен**. File watcher подхватывает автоматически.
- `/clear` → SessionStart `source=clear` → перечитывает hooks.
- `claude -c` / `--resume` → SessionStart `source=resume` → перечитывает hooks.
- Команды `/reload-hooks` нет — только file watcher или явный SessionStart.
- Оговорка: «normally» — edge-кейсы возможны. Для 100% гарантии — `/clear`. Проверить загрузку: `/hooks` (read-only список).

**Прецедент ошибки 2026-05-28 (EDUCATION session):** несколько раз сказал Антону «нужен рестарт для активации hooks», опираясь на ЭТО правило из памяти. При проверке справки через WebFetch — оказалось file watcher подхватывает сам. Класс ошибки: доверие устаревшему правилу из памяти вместо сверки с первоисточником. Связь: `self-corrections.md` #20 (устаревшие факты из памяти).

## 10. Не railroad — давай контекст, не сценарий

> *"Don't railroad: Give info, not step-by-step scripts; let Claude adapt."*

**У нас:** в `core.md`/`quality.md` десятки пошаговых SOP. Часть оправдана (deploy, security, blast-radius), часть — over-prescriptive. **Идея:** разделить на MUST (security, revenue) и GUIDELINES (style, organization).

## 11. Compound engineering через PR

> *"Tag Claude during code review with corrections; Claude auto-updates CLAUDE.md as part of PR itself (via GitHub Action)."*

**У нас:** `post-commit-learning.sh` есть. **Gap:** привязка к PR-ревью клиентом/Андреем отсутствует.

## 12. Session naming + fork

> *"`claude --name 'auth-refactor'`"* + `claude --resume <session-id> --fork-session`.

**У нас:** auto-naming через `session-namer.sh` + `cc-name`. **Gap:** `--fork-session` для параллельных экспериментов из общего baseline (3 версии КП от одной точки) не используется.

## 13. Переосмысление цикла > ускорение старого процесса

> Источник: тред [@bcherny 2026](https://x.com/bcherny/status/2060390852619272526) (зеркало [twitter-thread.com/t/2060390852619272526](https://twitter-thread.com/t/2060390852619272526)). Кейс Salesforce: проект 231 день → **13 дней**; один PR добавил 21 API-endpoint с полным тестовым покрытием; PR-ов больше, а инцидентов **−5%** (качество встроено в workflow агента, не «после»).
>
> *"The biggest win comes not from automating current work, but from rethinking the development cycle itself — remove steps, eliminate handoffs, let agents own tasks end-to-end."*

**Главная мысль:** максимальный выигрыш — НЕ ускорять текущий процесс, а **переосмыслить сам цикл**: убрать лишние шаги, убрать передачи ответственности (handoffs), дать агенту владеть задачей end-to-end.

**У нас (применимо, с оговоркой):**
- ✅ Это ровно курс `/combine` (очередь→выполнение→проверка→деплой→закрытие без остановок) + `parallel-task-orchestration.md` (рой сеньоров вместо последовательной работы) + встроенное качество (factcheck/qa-full.sh/хуки = «инциденты −5%»). Твит **подтверждает** наш вектор, нового действия не даёт.
- ⚠️ **Оговорка:** тезис «агент владеет end-to-end» у нас **ограничен**. CONFIRM-барьеры (контакт с клиентом, прод-деплой, деньги — `security.md`) — это НЕ «лишний handoff» для устранения, а защита от blast-radius. Убирать их по мотиву «agent owns everything» нельзя. Цифры Salesforce (231→13 дней) — про продуктовый код, к агентству SEO/маркетинга 1:1 не переносятся, переносится принцип.
- Перекликается с #10 «не railroad»: меньше пошаговых сценариев там, где агент может владеть результатом сам.

## Когда применять эти правила

- Перед длинной сессией (>200K tokens) — проверить env `CLAUDE_CODE_AUTO_COMPACT_WINDOW`
- При неудачном ответе Claude — использовать `/rewind`, не «уточняй промпт»
- При правке >3 файлов — Plan Mode (Shift+Tab×2)
- При параллельных экспериментах — `--fork-session` от общего commit'а

## Связанные правила

- `~/.claude/rules/self-corrections.md` — наш аналог mistake-log Cherny
- `~/.claude/rules/bulletproof-patterns.md` — challenge loop + 40% rule
- `artvision-data/docs/claude-code-improvements-2026-05-04.md` — roadmap из 12 пунктов улучшений
