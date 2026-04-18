# Claude Code Config Audit — 2026-04-17

Объект: `/Users/antonk/.claude/` (Anton, adw.artvision.pro@gmail.com)
Референс: docs.claude.com (Claude Code docs: settings, hooks, slash-commands, subagents, skills, memory, mcp, output-styles, statusline)
Режим: только отчёт, без правок. Все находки — предложения, не применённые изменения.

---

## TL;DR

- **5 CRITICAL** (несоответствия спецификации, потенциальные тихие фейлы хуков/permissions)
- **11 MEDIUM** (устаревшие паттерны, легаси, недоиспользованные фичи)
- **9 MINOR** (косметика, dead code, оверинженеринг)

**Топ-3 срочных фикса (≤ 30 минут вместе):**

1. **C2:** PostToolUse matcher `"Edit|Write"` пропускает MultiEdit → factcheck/lint не срабатывают на MultiEdit-правках (реально используется для пакетных правок TODO.md + PROJECTS.md).
2. **DEAD CODE:** 6 хуков в settings.json ссылаются на файлы с суффиксом `.pre-shared-20260415` — основные файлы отсутствуют, хуки молча фейлят: `pre-client-write.sh`, `pre-scp-factcheck.sh`, `pre-deploy-factcheck.sh`, `post-client-html-factcheck.sh`, `post-factcheck-autofix.sh`, `post-websearch-factcheck.sh`. Критично — вся factcheck-инфраструктура не работает.
3. **N9:** `settings.local.json` содержит sshpass/ftp пароли в plaintext (`SW_pass2025`, `cp02586,6CNgRdxX222`). Удалить.

---

## CRITICAL

### C1. Matcher в событиях, где он не применим
**Файл:** `/Users/antonk/.claude/settings.json`
**Что:** поля `"matcher": ""` стоят в `Stop`, `SessionStart` (блок 1 из 3), `PreCompact`, `PostCompact`.
**Спека:** `matcher` применим только для `PreToolUse`, `PostToolUse`, `PreCompact`. Для остальных поле игнорируется.
**Как чинить:** удалить `"matcher": ""` из Stop и PostCompact блоков. В SessionStart — первый блок можно оставить без matcher (ловит все типы) или разделить на startup/resume vs compact.

### C2. PostToolUse матчер `Edit|Write` пропускает MultiEdit
**Файл:** `settings.json`, блок `"PostToolUse"` → `"matcher": "Edit|Write"`
**Что:** все factcheck/lint/validate хуки (`post-edit-lint.sh`, `post-client-html-factcheck.sh`, `post-client-html-validate.sh`, `post-html-seo-check.sh`, `post-ux-cro-check.sh`, `post-data-collect.sh`, `post-client-context-log.sh`, `post-edit-autotest.sh`, `post-edit-skill-trigger.sh`) привязаны только к `Edit|Write`. MultiEdit не входит.
**Риск:** MultiEdit активно используется для пакетных правок → все проскакивают мимо factcheck и lint.
**Как чинить:** в PostToolUse matcher → `"Edit|Write|MultiEdit"`.

### C3. Permissions: `Bash(rm *)` — слишком широко
**Файл:** `settings.json`, строка 88
**Что:** `"Bash(rm *)"` в allow + только 6 строк в deny (`rm -rf /`, `rm -rf ~`, `rm -rf /*`, `> /dev/sda*`, `mkfs *`, `dd if=*`).
**Риск:** `rm -rf /Users/antonk/artvision-data` или `rm -rf /var/www` попадают под allow. `defaultMode: "bypassPermissions"` не помогает — наоборот, усугубляет.
**Как чинить:** убрать `Bash(rm *)` и добавлять точечно через settings.local.json по мере задач, ИЛИ расширить deny на частые destructive paths.

### C4. MCP naming в permissions
**Файл:** `settings.json`, строки 156-162
**Проблемы:**
- `"mcp__pencil"` без `__*` — вероятно не разрешает ни один pencil-tool
- `"mcp__plugin_playwright_playwright__*"` — неверный формат? Session-reminder выше показывает что реальные имена `mcp__claude_ai_Figma__*`, `mcp__pencil__*` и т.д. — не `plugin_<X>_<X>`.
**Как чинить:** запустить `/mcp` в Claude Code → взять точные имена серверов → обновить.

### C5. Отсутствует `$schema` поле
**Что:** добавить `"$schema": "https://json.schemastore.org/claude-code-settings.json"` первым полем. Даёт автокомплит и валидацию в IDE.

---

## MEDIUM

### M1. CLAUDE.md не использует `@import` синтаксис
**Файл:** `/Users/antonk/.claude/CLAUDE.md` (23 строки)
**Что:** файл содержит таблицу из 6 rules-файлов, но БЕЗ `@` префикса. Rules загружаются через хук `start-sync-settings.sh`, не через @import.
**Как чинить:** заменить на `@rules/core.md`, `@rules/context.md` и т.д. — стандартный механизм докей.

### M2. SessionStart matcher оптимизация
**Что:** блок 1 из 3 (без matcher) срабатывает на все типы старта включая compact → 10 хуков лишнего I/O при compact.
**Как чинить:** разделить на `matcher: "startup|resume"` (меню, restore, overdue) и `matcher: "compact"` (только post-compact-tasks).

### M3. Orphan hooks и .disabled файлы
**Орфаны (не упомянуты в settings.json):**
- `hooks/context-monitor.sh`, `save_session.py`, `post-frontend.sh`, `post-commit-learning.sh`, `sync-all-repos.sh`
- `_disabled-inject-knowledge.sh`, `_disabled-stop-knowledge-reminder.sh`
- `sync-all-repos.sh.disabled`
**Упоминаются в settings.json, но отсутствуют на диске** (есть только `.pre-shared-*` версии):
- `pre-client-write.sh`, `pre-scp-factcheck.sh`, `pre-deploy-factcheck.sh`
- `post-client-html-factcheck.sh`, `post-factcheck-autofix.sh`, `post-websearch-factcheck.sh`
**Критично:** 6 хуков в settings.json молча фейлят — вся factcheck-инфраструктура не работает.
**Как чинить:** переименовать `.pre-shared-20260415-131019` → основной файл (или восстановить из git).

### M4. 130 агентов без `model:` field
**Что:** `grep -c "^model:"` → 82 файла имеют, остальные ~130 не имеют.
**Правило:** `tokens.md` требует `model: opus` для всех субагентов.
**Риск:** без явного model агент наследует модель хоста. Если хост на sonnet — агент тоже на sonnet, нарушая внутреннее правило.
**Как чинить:** скрипт для массового добавления `model: opus` в frontmatter.

### M5. Loose `skills/game-factory.md`
**Что:** одинокий .md в корне skills/ не подхватывается Claude Code (нужен `skills/<dir>/SKILL.md`). Правильная версия `skills/game-factory/SKILL.md` уже есть.
**Как чинить:** удалить loose файл.

### M6. Архивные директории в skills/
**Что:** `.weekly-self-review-archived/`, `.weekly-maintenance-archived/`, `.page-create-archived/`, `.ant-visual-archived/`, `.ant-pages-archived/`, `.ant-deploy-archived/`, `artvision-workflow/SKILL.md.backup`.
**Как чинить:** перенести в `_archive/skills/` за пределы активной директории.

### M7. Timeouts для agents-in-the-office async-хуков
**Что:** все `.agents-in-the-office/hooks/claude-code.sh X` с `async: true` без `timeout`.
**Риск:** default timeout 60 сек может задерживать процесс при зависании.
**Как чинить:** добавить `"timeout": 10` для страховки.

### M8. PreCompact matcher `manual` vs `auto`
**Что:** сейчас `matcher: ""` ловит оба. Если handover-логика должна отличаться (ручной /compact vs авто) — разделить.

### M9. Statusline latency
**Файл:** `/Users/antonk/.claude/statusline.sh`
**Что:** 2 git-вызова × 2 сек timeout = до 4 сек latency.
**Как чинить:** кэш в /tmp на 5 сек, или один `git status --porcelain=v2 --branch`.

### M10. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — проверить статус
**Что:** экспериментальный флаг. На 2026-04 статус в docs не подтверждён.
**Как чинить:** проверить docs.claude.com и обновить если фича переименована/GA.

### M11. `output-styles/` пустая директория
**Что:** фича не используется. Либо создать 1-2 стиля (brief, verbose), либо удалить пустую папку.

---

## MINOR

### N1. `includeCoAuthoredBy` не выставлен (default true)
### N2. `enableAllProjectMcpServers` не установлен — для .mcp.json в проектах требуется подтверждение
### N3. `apiKeyHelper` / `awsAuthRefresh` — не нужны (Claude Max через OAuth)
### N4. `checkpointing` — default включено, явная конфигурация не требуется
### N5. JSON не поддерживает комментарии — большие блоки трудно навигировать. Решение: отдельный settings.README.md
### N6. ~36 orphan scripts в `scripts/` (browser-keepalive, cr.sh, heartbeat, idle-worker, memory-recall, ots-restamp, payment-reminder, suno-helper, vpn-switcher, zoom-auto-transcribe, voice-relay.sh.disabled, sync-all-sessions.sh.local, __pycache__/)
### N7. 215 агентов — многовато. Специфичные стеки (dotnet, elixir, flutter, kotlin) не нужны для Artvision → перенести в `agents/_unused/`
### N8. `commands/*.md` без явного `model:` — для code-review/evolve хотелось бы opus
### N9. **settings.local.json содержит пароли в plaintext**:
- `Bash(sshpass -p 'SW_pass2025' ssh ... attorneys@77.222.56.111 ...)` — ssh пароль
- `Bash(lftp ... -u cp02586,6CNgRdxX222 vh254.timeweb.ru)` — ftp пароль
**Срочно:** удалить эти строки. Проверить что settings.local.json в .gitignore.

---

## KEEP — хорошие паттерны

1. Разделение allow/deny в permissions
2. Многоуровневые SessionStart хуки (восстановление, меню, Asana overdue, sync) — сильная архитектура
3. Stop хуки с quality-check, smoothing-check, anti-rationalization — уникальная self-correction логика
4. Custom `statusline.sh` с git/cost/context% — полезная информация
5. Progressive disclosure skills (SKILL.md + references/ + templates/)
6. MCP через enabledPlugins (plugins подключают MCP автоматом) — современный паттерн
7. Skills с README и CHANGELOG (modx-cms, notebooklm, outreach-emails, skill-generator)
8. Отдельная MCP-секция в permissions
9. `skipDangerousModePermissionPrompt: true` + `defaultMode: "bypassPermissions"` осознанно для автономного режима

---

## MISSED FEATURES

1. `$schema` — валидация в IDE
2. `autoApprove` — альтернативный синтаксис permissions
3. `disabledMcpjsonServers` — явный disable project MCP
4. SessionEnd sync-хук — сейчас только agents-in-the-office async
5. output-styles — нет ни одного стиля
6. PreCompact matcher manual/auto — см. M8
7. `statusLine` явно в settings.json — сейчас implicit
8. CLAUDE.md `@imports` — см. M1
9. UserPromptSubmit с matcher для autotrigger skills

---

## DEAD CODE — кандидаты на удаление

**Hooks-орфаны:**
`context-monitor.sh`, `save_session.py`, `post-frontend.sh`, `post-commit-learning.sh`, `sync-all-repos.sh(+.disabled)`, `_disabled-inject-knowledge.sh`, `_disabled-stop-knowledge-reminder.sh`

**Hooks missing on disk, referenced in settings.json** (КРИТИЧНО):
`pre-client-write.sh`, `pre-scp-factcheck.sh`, `pre-deploy-factcheck.sh`, `post-client-html-factcheck.sh`, `post-factcheck-autofix.sh`, `post-websearch-factcheck.sh` — все существуют только как `.pre-shared-20260415-131019`.

**Skills:**
`skills/game-factory.md` (loose), `skills/.*-archived/`, `skills/artvision-workflow/SKILL.md.backup`

**Scripts:**
`factcheck-v2.py.pre-shared-*`, `factcheck-strict.py.pre-shared-*`, `factcheck-autofix.py.pre-shared-*`, `voice-relay.sh.disabled`, `sync-all-sessions.sh.local`, `__pycache__/`

**Agents:**
`strict-factchecker.md.pre-shared-20260415-131019`, 130 агентов без `model:` field (многие специфичны для стеков вне Artvision)

**Settings.local.json:**
~300 одноразовых Bash permissions + пароли в plaintext (N9)

---

## Приоритеты

| P | Блок | Время | Эффект |
|---|------|-------|--------|
| P0 | DEAD CODE — восстановить .pre-shared-* хуки | 10 мин | Factcheck-инфра снова работает |
| P0 | C2 — MultiEdit в matcher | 2 мин | Lint/factcheck на MultiEdit |
| P0 | N9 — удалить пароли из settings.local.json | 5 мин | Security |
| P1 | C3 — сузить `Bash(rm *)` | 10 мин | Safety |
| P1 | C1 — matcher cleanup | 10 мин | Спека |
| P1 | M4 — model: opus в 130 агентов | 20 мин | tokens.md compliance |
| P2 | C5 + M1 — $schema + @imports | 10 мин | IDE |
| P2 | M3 + DEAD — чистка hooks/ | 20 мин | Hygiene |
| P3 | MISSED — statusline explicit + output-styles | 30 мин | Feature completeness |

**P0+P1 = ~1 час. Этого достаточно для закрытия всех реальных багов.**

---

*Отчёт сгенерирован 2026-04-17 без правок файлов.*
