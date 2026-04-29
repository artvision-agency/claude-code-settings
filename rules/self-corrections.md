# Самокоррекция — ошибки которые НЕЛЬЗЯ повторять

> Если повторяешь ошибку — ты тупишь. При новой ошибке — ДОПИСАТЬ СЮДА.

## Топ ошибки (сжатые)

1. **Потеря контекста** → читай TODO.md + MEMORY.md + context-log.md ПЕРЕД вопросом
2. **TaskCreate забывается** → СРАЗУ при старте для всех pending. Не после напоминания
3. **Фактчекинг не подключён** → правило + хук/скрипт. Не "запишу" — АВТОМАТИКА
4. **Спрашиваю вместо поиска** → grep, git log, clients/, tokens.json — потом спрашивай
5. **Агент без Bash для деплоя** → general-purpose для scp/deploy
6. **Бот падал 3 дня (#7)** → после деплоя: 5 мин мониторинг, healthcheck, git-only
7. **Compaction теряет обещания (#11)** → парсить summary → TaskCreate для каждого pending
8. **Правила в md без хука** → МЕТА: правило + автоматика, иначе забудется

## Чеклист старта (НЕ ПРОПУСКАТЬ)

- [ ] `git pull` все репо
- [ ] TODO.md текущего контекста → TaskCreate для pending
- [ ] После compaction: summary → TaskCreate
- [ ] Показать меню перекрёстка

### 8. "Готово" без прогона qa-full.sh (inциденты 2026-04-18)
- **Проблема:** 3 раза подряд сказал "всё готово" без прогона QA-скрипта → Антон ловил руками пробелы (security CRIT, no E2E, no integration)
- **Решение:**
  1. `~/.claude/rules/qa-enforcement.md` — жёсткое правило
  2. `<repo>/scripts/qa-full.sh` — единая команда прогонки
  3. Hook `~/.claude/hooks/pre-push-qa-check.sh` — блокирует push если FAIL
  4. Перед каждым "готово"/"работает"/"production-ready" — прогнать `qa-full.sh` и показать PASS N/N

### 10. Strip/clean скрипт без regression-check (инциденты ant-partners 2026-02-24, 2026-03-03)
- **Проблема:** `strip_inline_duplicates.py` удалил 157 секций из 29 JSON, валидатор показал «29/29 PASS» (валидация по наличию класса в `<style>`, не по DOM). Через неделю — `fix_clean_revision.py` сократил с 564 → 72 файла без явного бэкапа в session-логе.
- **Решение:**
  1. baseline `.section-counts.json` → если секций меньше предыдущей версии → FAIL до approval
  2. Хук `pre-strip-script-guard.sh` PreToolUse на Bash с regex `python.*(strip|clean|fix_inline|fix_clean).*\.py`, требует `--dry-run` первым прогоном
  3. `git stash` ИЛИ feature branch перед запуском
- **Активация:** `~/.claude/hooks/pre-strip-script-guard.sh` зарегистрирован в settings.json под matcher Bash. Bypass: `STRIP_FORCE=1`.

### 9. TaskCreate пропуск даже при включённом SessionStart-хуке (инцидент 2026-04-18/19)
- **Проблема:** SessionStart-хуки `start-todo-tasks.sh` + `start-todo-taskcreate.sh` инжектят 180 pending с императивом "ОБЯЗАТЕЛЬНО вызови TaskCreate". Я всё равно пропустил — когда Антон дал первый prompt ("оферы НБКИ"), переключился на него и reminder потерял salience после 2-3 reply.
- **Корень:** SessionStart-инжекция одноразовая. UserPromptSubmit-хуки (5 штук) не проверяли TaskCreate.
- **Решение (развёрнуто 2026-04-19):**
  1. `~/.claude/hooks/prompt-taskcreate-nag.sh` — UserPromptSubmit-хук
  2. Логика: если pending>0 И в транскрипте сессии НЕТ "TaskCreate" И prompts<=10 → инжектить императив с top-5 high
  3. Self-disable после первого TaskCreate или >10 turns
  4. Активация на новой сессии или через `/hooks` reload
- **Слой 2 (развёрнут 2026-04-27):** `~/.claude/hooks/pre-tool-block-no-taskcreate.sh` — PreToolUse, matcher `""` (все инструменты). Whitelist: Task*/Read/Grep/Glob/ToolSearch/Skill/ScheduleWakeup/AskUserQuestion + Bash для read-only (git status|pull|fetch|log|diff, ls/pwd/cat/head/tail/grep/find/wc, python3 -c, curl без -X POST/PUT/DELETE). Self-disable: `/tmp/taskcreate-done-{session_id}` после первого TaskCreate ИЛИ если в transcript уже есть `"name":"TaskCreate"`. Bypass: `TASKCREATE_FORCE=1`. Тесты: 13/13 PASS (`/tmp/test-taskcreate-hook.sh`).

## МЕТА-ПРАВИЛО: инцидент → хук, не «запомню»

Когда деструктивный инцидент случился — **обязательно создать PreToolUse-хук** с детерминистичной проверкой. Не полагаться на «запишу в правило» / «буду внимательнее» / «теперь знаю».

Причина: правила в md-файлах — это **моя память**, которая в моменте не срабатывает (см. инциденты #8, #9 и инцидент 23.04 с потерей коммита 9973dc3 — все три случая правило было, но я его не вспомнил). Хук работает на уровне харнеса, не зависит от моего внимания.

Алгоритм после нового инцидента:
1. Идентифицировать паттерн (regex по команде / пути / args)
2. Написать `~/.claude/hooks/pre-<thing>-guard.sh` с exit 1 + bypass через env
3. Зарегистрировать в `~/.claude/settings.json` под нужный matcher (Bash / Edit / Write)
4. Тест: 3+ кейса блокировки + 3+ кейса пропуска + bypass
5. Дописать в текущий файл строку под «Активные защитные хуки»

### Активные защитные хуки

| Хук | Matcher | Прецедент | Bypass env |
|-----|---------|-----------|-----------|
| `pre-push-qa-check.sh` | Bash | 18.04 — push без QA, 3× security CRIT в проде | `QA_SKIP=1` |
| `pre-vps-git-guard.sh` | Bash | 23.04 — потеря коммита 9973dc3 через `ssh git pull --rebase` | `VPS_GIT_FORCE=1` |
| `pre-tmp-write-guard.sh` | Write+Edit | 23.04 — `/tmp/gen_dental_reports.py` потерян при reboot | `TMP_WRITE_FORCE=1` |
| `pre-cleanup-tokens-check.sh` | Bash | 17.04 — `rm -rf ~/.npm` убил YouTube OAuth (invalid_grant) | `CLEANUP_FORCE=1` |
| `pre-client-work.sh` | Edit+Write | ant-partners 18/24/28.02 — пропуск Pre-Task Protocol → 29 страниц переделаны | `PRETASK_FORCE=1` |
| `pre-strip-script-guard.sh` | Bash | ant-partners 24.02 — strip без regression-check, 157 секций потеряно | `STRIP_FORCE=1` |
| `pre-bash-resource-guard.sh` | Bash | 26.04 — все 4 ttys claude упали 2× за 2 часа, OOM подозрение (free RAM ~42MB, диск 97%) | `RESOURCE_FORCE=1` |
| `prompt-taskcreate-nag.sh` | UserPromptSubmit | 18-19.04 — TaskCreate пропуск при 180 pending (Layer 1, мягкий) | (auto-disable) |
| `pre-tool-block-no-taskcreate.sh` | PreToolUse `""` (все) | 27.04 — Антон требует жёсткий блок (Layer 2) | `TASKCREATE_FORCE=1` |
| `pre-tool-recap-goal-check.sh` | PreToolUse `""` (все) | 29.04 — recap «Цель сессии» пустая на первом Edit/Write/Bash 2 раза подряд (sessionId c0f1dfaa) | `RECAP_GOAL_FORCE=1` |
| `inject-challenge-reminder.sh` | UserPromptSubmit | магические цифры без источника | (auto после Skill) |
| `stop-hallucination-detect.sh` | Stop | детект галлюцинаций в ответе | — |

При добавлении нового хука — **сразу обновить таблицу**.
