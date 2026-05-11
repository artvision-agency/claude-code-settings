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

### 11. Shorthand «не нашёл» при поверхностной проверке (инцидент 2026-05-08, AVBOTS_restore)
- **Проблема:** Антон написал «п/ф ?», я загрузил skill `shorthand` (словарь), не нашёл «п/ф» там и ответил «нет в словаре». Антон: «ты врешь, было МНОГО раз». При широком grep оказалось — «п/ф» = «план/факт», встречается в memory + 10+ session jsonl + recap d172a931, прошлый Claude уже расшифровал.
- **Корень:** SKILL.md `shorthand` — **не единственный источник** короткостей. Антон копит сокращения в живых сессиях; если что-то не в словаре — это НЕ значит «не существует», скорее «не успели внести в словарь».
- **Решение:**
  1. При неизвестном shorthand — **не возвращать «нет в словаре»** даже если skill пустой
  2. Сделать grep по 4 источникам параллельно: `~/.claude/projects/-Users-antonk/memory/`, `~/.claude/projects/-Users-antonk/*.jsonl` (последние 30 дней), `~/artvision-data/sync/recaps/`, `~/.claude/skills/shorthand/SKILL.md`
  3. Если найдено в session jsonl где предыдущий Claude уже расшифровал — взять ту расшифровку
  4. Если не найдено нигде — спросить **по контексту**, а не «нет в словаре»
- **Кандидат-хук:** `pre-shorthand-grep.sh` — если ответ Claude содержит «нет в словаре» / «не нашёл» по shorthand-теме без признаков grep по jsonl → инжект напоминания. (TBD)
- **Также:** дополнить skill `shorthand` записью «п/ф = план/факт» (отдельная задача).

### 12. Telethon session expired без proactive health check (инцидент 2026-05-08, AVBOTS_restore)
- **Проблема:** в задаче «прочитать чат @avportal_bot» Telethon session оказалась expired (last auth 2026-05-01, 7 дней назад). Скрипт упал на интерактивном prompt'е телефона. Acceptance не закрыт.
- **Корень:** session-файл стареет молча. Нет проверки «давно ли auth» перед задачами требующими Telethon.
- **Решение:**
  1. SessionStart-хук: если `~/artvision-data/.claude_temp_scripts/tg_userbot.session` mtime > 3 дня → warn + предложить re-auth
  2. Wrapper-script `tg_chat_reader.py` — перед запуском проверять connect+is_user_authorized, при fail выводить чёткое «нужна re-auth: запусти `tg-reauth.sh`»
  3. Skill `tg-chat-export` обновить с pre-flight check
- **Hard requirement:** re-auth = только интерактивно (Антон вводит код из TG), Claude не может сам.

### 14. qcomment accept вслепую — деньги за «На проверке» (инцидент 2026-05-11)
- **Проблема:** `qcomment-accept-pending.py accept --all` приняло 2 коммента (97494004 + 97491553) со статусом «На проверке» на скриншотах Anna762. Деньги ушли исполнителю, но Яндекс модерация не подтвердила публикацию (robot_find=0, в live-snapshot не найдены). Откат заблокирован qcomment API (error 603).
- **Корень:** скрипт не проверял что отзыв реально published в Яндексе перед /api/revision operation=0.
- **Решение:**
  1. Правило `~/.claude/rules/qcomment-accept-only-published.md` — принимать только если найден в live OR на скрине явно «Опубликован»
  2. Hard guard в `qcomment-accept-pending.py:_live_match()` — проверяет match по author/text в свежем live-reviews snapshot. Без match → SKIP, с `--force` опционально.
  3. Smoke pass: новый pending 97539079 «Анна / припотолочную люстру» найден в live → guard пропустил accept ✓
- **Стоимость инцидента:** 40-74 ₽ (20-37 × 2), не списано с баланса (50→50 ₽), значит деньги списались ранее при `/api/payproject`.

### 13. Self-symlinks в hooks/ → ELOOP «Too many levels of symbolic links» (инцидент 2026-05-09)
- **Проблема:** 4 Stop-хука падали с `Too many levels of symbolic links`: `stop-skill-audit.sh`, `stop-asana-skill-comment.sh`, `stop-recap-completeness.sh`, `stop-cost-summary.sh`. Похожие самосимлинки нашлись ещё в 4 хуках + 6 scripts + 1 commands — ELOOP не выстрелил только потому что в текущей сессии не было соответствующих событий.
- **Корень:** коммит `10a86b4a` (08.05 22:41, Anton K) одним махом конвертировал 17+ файлов из real-files в **симлинки на самих себя** (target = `/Users/antonk/claude-code-settings/hooks/X.sh`, который и есть сам файл). Какой-то sync/install-скрипт на 3-й машине вместо `ln -s "$source" "$target"` сделал `ln -s "$target" "$target"`. После git add/commit и push — поломка распространилась на все 3 аккаунта.
- **Восстановлено:** 13 файлов из git history (предыдущие коммиты `93d2e44c` / `b047fc8f` / `dc5943de`), коммиты `0cbe308`, `ca9736f`, `f6d9c8c` в `claude-code-settings`. После: `~/.claude/hooks/*` симлинки разрешаются → `~/claude-code-settings/hooks/*` → реальные файлы.
- **Кандидат-хук:** `pre-symlink-self-loop-guard.sh` — PreToolUse(Bash) на `git add|commit|push`, сканирует staged изменения на mode `120000` где target == path. Блокирует commit. Bypass: `SYMLINK_SELF_OK=1`.
- **Кандидат-проверка в SessionStart:** запускать `find ~/claude-code-settings -type l -name '*.sh' -exec sh -c '[ "$(readlink {})" = "$(realpath -s {})" ] && echo BAD: {}' \;` — если что-то найдено, инжектить warn в стартовое сообщение.
- **Также:** найти sync-скрипт-источник на 3-й машине (вероятно `bootstrap-new-machine.sh` или `install-skill-enforcement.sh`) и пофиксить логику симлинкования.

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
| `pre-bash-topvisor-guard.sh` | Bash | 29.04 — ДВАЖДЫ за одну сессию сжёг 100 RUB баланса Антона: фильтр `NOT_IN [0]` на `edit/positions_2/checker/go` запустил съём по 9 чужим проектам (vlpco, dsk-home, stomatiko, otido), 529 ключей × ~0.19 RUB. Блокирует: NOT_IN, MATCH '%', EXISTS, GREATER/LESS, checker/go без EQUALS, EQUALS [0], EQUALS []. Тесты: 8/8 PASS | `TOPVISOR_BROADCAST_FORCE=1` |
| `pre-scp-kp-diff.sh` | Bash | 05.05 — АН-НУР 3 итерации правок из-за пропущенных элементов starclinic при grep-by-code сравнении (domain-pill, advm-mark в footer, бэйдж AdvertMed, brand strip, плашки «Что даёт оценку», «Окно ROI», «Конкурентная гипотеза», «Формат AdvertMed», реквизиты клиники). Хук читает `clients/<name>/config.yaml` → `reference_kp:`, требует прогона `kp-visual-diff.py` (skill `kp-visual-diff`) перед scp клиентского КП. Скилл рендерит оба HTML в PNG 1280×720@2x через Playwright + pixel-diff Pillow + side-by-side HTML отчёт. | `KP_DIFF_SKIP=1` |
| `prompt-taskcreate-nag.sh` | UserPromptSubmit | 18-19.04 — TaskCreate пропуск при 180 pending (Layer 1, мягкий) | (auto-disable) |
| `pre-tool-block-no-taskcreate.sh` | PreToolUse `""` (все) | 27.04 — Антон требует жёсткий блок (Layer 2) | `TASKCREATE_FORCE=1` |
| `pre-tool-recap-goal-check.sh` | PreToolUse `""` (все) | 29.04 — recap «Цель сессии» пустая на первом Edit/Write/Bash 2 раза подряд (sessionId c0f1dfaa) | `RECAP_GOAL_FORCE=1` |
| `pre-kp-bred-block.sh` | PreToolUse `Write\|Edit` | 30.04 — strict-агенты нашли 49 CRITICAL в 39 КП за месяц (выручка клиента в рублях, UNCONFIRMED маркеры в видимом тексте, artvision.pro упоминания, «Лор-Альянс»-фейковый конкурент). Системные хуки + auto-fix + scanner | `KP_BRED_OK=1` |
| `pre-client-lexicon.sh` | PreToolUse `Write\|Edit` | lexicon-lint для clients/*/presale/*/kp/*: AI/нейросети запрещены, бренд написание, клише. **Whitelist 05.05:** `*/clients/*/CLAUDE.md\|README.md\|context-log.md\|lexicon.yaml` (служебные файлы для агента, не клиента) | `LEXICON_INTERNAL_OK=1` |
| `inject-challenge-reminder.sh` | UserPromptSubmit | магические цифры без источника | (auto после Skill) |
| `stop-hallucination-detect.sh` | Stop | детект галлюцинаций в ответе | — |

При добавлении нового хука — **сразу обновить таблицу**.
