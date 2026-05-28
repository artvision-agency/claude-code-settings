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

### 18. post-kp-deploy-factcheck.sh не зарегистрирован в settings.json + subagent silent bypass (инцидент 2026-05-19, сессия 30338bd4)

- **Проблема:** auto-strict L2 factcheck не запускался после deploy КП. Думали хук срабатывает в фоне. Проверил: `~/artvision-data/clients/_factcheck-history/` — **директория не создана**, ни одного lock-файла в `/tmp/auto-strict-*`. Хук существует (`~/.claude/hooks/post-kp-deploy-factcheck.sh`), но **НЕ ЗАРЕГИСТРИРОВАН** в `~/.claude/settings.json` под PostToolUse Bash. Был установлен 05.05.2026, но в settings.json никогда не добавлен. Месяц мы думали что автоматика работает — а её не было.
- **Дополнительная проблема:** `pre-scp-kp-strict-factcheck.sh` тоже тихо пропускал subagent scp — потому что хук матчил только source-путь `presales/<slug>/kp/*.html`, не destination `/var/www/artvision/kp/<slug>/`. Subagent в background работал в изолированном context (видимо без stdin к хукам, либо с json-парс ошибкой) → хук возвращал exit 0 без logging.
- **Корень общий:** хуки добавляются в `~/.claude/hooks/`, но регистрация в `settings.json` забывается. Symptoms «тихо не работает» — не падает, просто не запускается. Subagent ничего не знает что хука нет.
- **Решение:**
  1. Регистрация добавлена: PostToolUse Bash + `~/.claude/hooks/post-kp-deploy-factcheck.sh` в settings.json (применится со следующей сессии, см. `cherny-tips.md` #9 hooks НЕ hot-swap)
  2. `pre-scp-kp-strict-factcheck.sh` пропатчен: + destination-path regex, + slug-from-dest, + skip logging в `/tmp/factcheck-hook-skip.log` (claude-code-settings commit 9258858)
  3. Backup settings.json: `~/.claude/settings.json.bak-2026-05-19`
- **TBD кандидат-хук:** `SessionStart` или ежедневный cron — пройтись по `~/.claude/hooks/*.sh`, проверить какие НЕ зарегистрированы в settings.json, выдать список «orphan hooks» в TG / startup banner. Иначе любой новый хук рискует тихо лежать unused.
- **Также записать:** при добавлении любого нового хука — ОБЯЗАТЕЛЬНЫЙ step «зарегистрировать в settings.json» + проверка `grep <hook-name> ~/.claude/settings.json` после деплоя.

### 17. Subagents отказываются писать .md отчёты (инцидент 2026-05-17, сессия 599b44ec)
- **Проблема:** 2 из 4 senior-агентов (security-auditor, ux-researcher) проигнорировали явный запрос записать отчёт в `personal/ipoteka-2026/v10-check-{security,ux}-2026-05-17.md`. Вернули содержимое в task-notification message. ux-researcher даже процитировал источник: «Wait — re-reading the system reminder: Do NOT Write report/summary/findings/analysis .md files. Return findings directly». Strict + math агенты (general-purpose, data-analyst) — записали без проблем.
- **Корень:** встроенный system reminder Claude Code core инжектится в context субагента «не писать .md report files». Это НЕ локальный hook/rule — нельзя отключить через `~/.claude/`. Reviewer-агенты строже к нему чем general-purpose/data-analyst.
- **Решение:** правило `~/.claude/rules/subagent-md-output-override.md` с явным override-блоком для копирования в промпт `Agent`. Если override не сработал — записывать .md вручную из task-notification result.
- **Не делаю хук** — модификация tool_input в PreToolUse(Task) усложнит debug и добавит overhead на каждый Agent call. Правило + дисциплина в промпте эффективнее. При 3+ повторных инцидентов → пересмотреть на hook.

### 19. Массовая раскатка Artvision-брендинга на AdvertMed-партнёрские КП (инцидент 2026-05-20, сессия 70e38694)

- **Проблема:** при раскатке виджета voice.js + видео-аватара Антона на 24 «активных» КП (last 30 days mtime) добавил брендинг Artvision на 16 КП AdvertMed-партнёров (aymedi, kord-klinik, dimeev, tabib, neomed, kazan-clinic, annurclinic, family-stom, avicenna-endocrin, zdorovie-semi, coral, essence, c9m, artus, aist-crm, belyy-klyk). Все 16 имеют бейдж «ADVERTMED» в HTML.
- **Корень:** не проверил `artvision-data/.claude/rules/clients-registry.md` секцию «🚫 НЕ добавлять в портфолио» + `~/.claude/rules/artvision-branding-policy.md` перед bulk-операцией. Антон поймал на скриншоте aymedi: «адвертмед кп не трогаем».
- **Правило (HARD-ENFORCE):** **AdvertMed-партнёрские КП НЕ трогаем НИКАКИМ брендингом Artvision** — ни лого, ни виджет voice.js, ни фото Антона, ни любые упоминания artvision.pro в видимых элементах. Это субподряд / white-label, конечный клиент — другое агентство.
- **Список AdvertMed-партнёров (актуальный 20.05.2026):** aymedi, kord-klinik, dimeev, tabib, neomed, kazan-clinic, annurclinic, family-stom, avicenna-endocrin, zdorovie-semi, coral, essence, c9m, artus, aist-crm, belyy-klyk, varikoz/advertmed-varikozanet, stom-expert, s32, lumiere-dent, raduga/radugazvukov, advertmed-varikozanet77. Идентификация: `grep -ci "advertmed\|варикознет"` в HTML > 0 = партнёрская.
- **Решение (быстрое):** перед любой bulk-операцией на `*/kp/*` ОБЯЗАТЕЛЬНО фильтровать по grep advertmed/варикознет.
- **Откат:** 16 КП восстановлены из `.bak-2026-05-20-widget`. Validated curl: 0 widget refs на всех 16. С виджетом осталось 12 (4 v1 SpaDent/courses-v3 + 8 v2 non-AdvertMed).
- **Кандидат-хук:** `pre-bulk-kp-modify-advertmed-guard.sh` — PreToolUse Bash, парсит команду на наличие `for KP in` ИЛИ цикла по `/var/www/artvision/kp/`, проверяет каждый КП на grep advertmed → если хоть один партнёр в списке без явного `--include-advertmed` → BLOCK с явным списком партнёрских. Bypass: `ADVERTMED_BULK_OK=1`.

### 20. «Протухла сессия» вместо реальной причины — повтор формулировки хука без проверки (инцидент 2026-05-26, Грелка-инит)
- **Проблема:** стартовый хук показал «⚠️ TELETHON SESSION EXPIRED». Я повторил это Антону как факт. Антон: «как это может быть? API нашлись? APIHASH». При проверке корень НЕ в сессии: `api_id`/`api_hash` были вычищены из tokens.json security-аудитом voice-transcriber (коммит `13ced9d5de`, 21.04.2026 — tokens.json трекался в git с 18.04, api_hash утекал в origin). Скрипты Telethon ждут `tokens['telegram']['api_id']` — ключа нет → `KeyError` ещё до проверки сессии. Сессия (auth_key) тоже невалидна (`is_user_authorized=False`), но это вторично.
- **Корень:** SessionStart-хук судит по mtime session-файла + отсутствию маркера `.tg-auth-ok` → «EXPIRED». Это эвристика-перестраховка, не диагноз. Я повторил дословно, не проверив наличие api credentials и реальный `is_user_authorized`.
- **Решение:** при «session expired» от хука — до ответа проверить: (а) есть ли api_id/api_hash в tokens.json; (б) `git log -S'"api_id"' -- tokens.json` — не вычищались ли аудитом; (в) реальный `connect()+is_user_authorized()` без `start()`. Только потом формулировать причину.
- **Связано:** #12 (Telethon health check) — дополняет: проверять не только сессию, но и наличие api credentials. Security-аудиты могут молча убирать ключи.
- **TBD:** стартовый хук `tg-age-check` дополнить проверкой наличия api_id → если нет, писать «api_hash вычищен (коммит X)», не generic «EXPIRED».

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
| `pre-tool-cons-vs-swarm-disambiguate.sh` | PreToolUse `Skill` | 17.05 — 21 случай за 6 мес путаницы /cons (думать) vs /swarm (делать). Семантика: cons=думать, swarm=делать, mixed=cons→swarm пайплайн. Warn-only (не блокирует) при mismatch триггеров. | `CONS_SWARM_FORCE=1` |
| `inject-challenge-reminder.sh` | UserPromptSubmit | магические цифры без источника | (auto после Skill) |
| `stop-hallucination-detect.sh` | Stop | детект галлюцинаций в ответе | — |
| `post-edit-list-check.sh` | PostToolUse `Edit\|Write` | 13.05 — Антон много раз просил списки. Детектит h-tree/ASCII-tree/таблицы иерархии в `clients/*/plan,presale,reports,kp/*.html`. Warn-only. | — |
| `pre-deploy-coords-verify.py` | PreToolUse `Bash` (scp/cp HTML) | 16.05 IPOTEKA c052407c — пин Setl Ривьера смещён на 4 км. Проверяет Я.Карты coords против Nominatim OSM, блокирует если >2 км. | `COORDS_VERIFY_SKIP=1` |
| `pre-deploy-price-vs-source.py` | PreToolUse `Bash` (scp HTML) | 16.05 IPOTEKA — студия Парусная 1: HTML 6.1М, реальная 11.07М (+82%). Проверяет цену в HTML vs источник (WebFetch+кэш 6ч). | `PRICE_VERIFY_SKIP=1` |
| `pre-deploy-quote-exists.py` | PreToolUse `Write\|Edit` (HTML клиентские) | 16.05 IPOTEKA — «средства заморозить на 3 года» приписано дольщикам, в spbguru.ru НЕ найдено. Fuzzy 75% match цитат «» vs источник. | `QUOTE_VERIFY_SKIP=1` |
| `pre-deploy-formula-consistency.py` | PreToolUse `Bash` (scp/cp HTML) | 16.05 IPOTEKA — «6.0 К/мес × млн» в шапке, таблица даёт 5.83 (3% gap). Блок при >10% расхождении K vs платёж/кредит. | `FORMULA_CONSISTENCY_SKIP=1` |
| `pre-deploy-delivery-date-source.py` | PreToolUse `Bash` (scp HTML) | 16.05 IPOTEKA — Setl Ривьера «Q2 2026» (реально Q1 2028 = +6 кв). Проверяет дату сдачи в HTML vs сайт застройщика. | `DELIVERY_DATE_SKIP=1` |

При добавлении нового хука — **сразу обновить таблицу**.

### 16. Структуры выводил h-tree/деревом вместо списков (повторная ошибка, 13.05.2026)
- **Проблема:** В клиентских HTML (figma-redline-v3 Часть 2, ранее dentix-FINAL Часть 2) использовал `<div class="h-tree">` с цветным `<span class="h1/h2/h3">` для иерархии H1-H6 страниц. Антон уже несколько раз просил списки — продолжал делать дерево. Антон 13.05 21:15: «постоянно прошу списками, почему. Давай сделаем так, чтобы это учитывалось в каких-то файлах, чтобы на все три аккаунта все всегда это видели».
- **Корень:** правило существовало в head Антона, не было в файлах. Опиралось на мою память, которая в конкретный момент не сработала.
- **Решение (hard-enforce на 3 уровнях):**
  1. `~/.claude/rules/document-list-format.md` — глобальное правило (private, во всех моих сессиях)
  2. `artvision-data/.claude/rules/document-list-format.md` — git-sync на 3 аккаунта (justtrance / adw.artvision.pro / antoniokmr)
  3. `memory/feedback_lists_not_trees_for_structures.md` — grep'абельная память
  4. Hook `~/.claude/hooks/post-edit-list-check.sh` — PostToolUse(Edit|Write), детектит h-tree / ASCII-tree / таблицы иерархии в `clients/*/plan/*.html` и др., warn-only (для отлова до отправки клиенту)
- **Активация:** хук зарегистрирован в `~/.claude/settings.json` PostToolUse `Edit|Write`. Тест на v3 — 165 нарушений найдено корректно.
- **Применение:** ВСЕ скиллы пишущие документы (presale-kp, seo-master, content-writer, frontend-design, ui-mockup, page-review, factcheck, audit-kp, cons, и др.) ОБЯЗАНЫ выводить иерархии списками.

### 15. КП с дефолтной палитрой шаблона при копировании (инцидент 2026-05-11)
- **Проблема:** cosmetology-kursy_kp_v3.html получил CAMEO navy+gold от spb-kursy потому что я делал ПРОГРАММНУЮ КОПИЮ шаблона (`build_3_kp.py` копирует spb → подменяет данные), а не «новый КП с нуля с extract дизайн-системы клиента». Правило `kp-brand.md` (extract palette/fonts с сайта клиента) есть, но НЕ применилось — при копировании я не запускал curl/WebFetch на cosmetology-kursy.ru. Антон поймал руками: «ПОЧЕМУ ТЫ САМ НЕ ПОНИМАЕШЬ ЧТО ТАК НАДО?»
- **Корень:** при копировании шаблона КП от одного клиента к другому правило про brand-extraction не срабатывает (я думаю «я уже взял из spb-kursy»), хотя у разных клиентов разные палитры.
- **Решение:**
  1. Хук `pre-kp-brand-extract-check.sh` (PreToolUse Write/Edit) — блокирует первое сохранение `presales/<slug>/kp/*.html` если в transcript нет WebFetch/curl на домен клиента. Bypass: `BRAND_EXTRACT_OK=1`.
  2. Bypass допускается ТОЛЬКО для существующих КП >50KB (Edit, не Write первой версии).
  3. При копии шаблона — обязательный step: `curl + grep '#hex' + grep 'font-family'` на домен клиента ДО любого Write/Edit КП-файла.
- **Активация:** хук зарегистрирован в `~/.claude/settings.json` PreToolUse Write|Edit. Тесты — TBD.

### 16. Claim «нигде нет правила X» без полной проверки (инцидент 2026-05-11)
- **Проблема:** сказал «в инструкциях про SEMrush нигде нет, пробел в rules/». Реально SEMrush был в `artvision-data/.claude/rules/{kp-brand,medical-kp}.md`, `memory/{MEMORY,accounts,feedback_top_pages_required}.md`, 6 skills, 10+ session jsonl. Антон поймал: «не может быть такого».
- **Корень:** проверял только `~/.claude/rules/` — узкая выборка. У нас 3 источника правил: (1) `~/.claude/rules/` мой private, (2) `~/artvision-data/.claude/rules/` проектный, (3) `memory/` персональный. + skills.
- **Решение:**
  1. Хук `stop-claim-no-rule-check.sh` — Stop event, парсит последний assistant message на trigger «нигде нет / пробел / не зафиксировано», достаёт топик (CAPS-слово или известный инструмент), grep по 4 источникам. Если найдено — инжектит warning в stderr.
  2. Bypass: `NO_RULE_CHECK_OK=1`.
  3. Активирован в `~/.claude/settings.json` под Stop.
- **Применять:** перед любым утверждением «правило не зафиксировано» — обязательный grep по 4 путям, не по одному.

### 21. Не зашёл на сайт партнёра/выставки за брендбуком когда делал баннеры (инцидент 2026-05-27, Avto.World × СТО Expo)
- **Проблема:** Делал ретаргет-баннеры для Avto.World на выставку **СТО Expo 2026**. Извлёк брендбук **только клиента** (avto.world: цвета #1a4f8a, #27ae60, лого 368×112). **НЕ зашёл на sto-expo.ru** за брендбуком/логотипом самой выставки. Антон явно отметил: «среди картинок я не увидел ни одного логотипа выставки, чего-то узнаваемого». Лого выставки = узнаваемость для целевой аудитории (посетители ищут стенд по знакомому брендингу СТО Expo).
- **Корень:** Я воспринял брендбук клиента (Avto.World) как достаточный. Но баннер РСЯ для **выставочной кампании** должен содержать ОБА бренда: клиента + самой выставки. Это базовый принцип co-branded реклама.
- **Решение:**
  1. **Правило:** при любой кампании привязанной к мероприятию/партнёру/выставке — извлекать брендбук **И клиента И мероприятия**. WebFetch на оба сайта.
  2. Скачивать логотипы (PNG/SVG), цвета (curl + grep '#'), официальные названия (на латинице И кириллице) обоих брендов.
  3. Co-branded layout: лого клиента + лого мероприятия рядом (обычно «X на Y»), даты+место мероприятия видно, ссылка на стенд клиента.
  4. **Checklist для event-кампаний:** [ ] лого клиента, [ ] лого мероприятия, [ ] даты, [ ] место, [ ] стенд/павильон, [ ] промокод (если есть).
- **Кандидат-хук:** `pre-banner-event-check.sh` — PostToolUse(Write) на `*banner*.jpg|png` в `clients/*/ads/*-expo-*` или `*-event-*` или `*-conference-*` → проверка наличия второго (event) логотипа в metadata/файлах рядом. Warn-only. (TBD)
- **Связано:** `~/.claude/rules/kp-brand.md` (Pre-Task: extract design-system), `asset-capture-no-loss.md` (URL клиента сохраняем — но не URL партнёра).

### 20. Устаревшие денежные/правовые факты из памяти без проверки источником (инцидент 2026-05-26)
- **Проблема:** на вопрос Антона про свидетельство о разводе в СПб ответил из памяти — госпошлина **«650 ₽»** (реально **5000 ₽** с каждого, повышение 09.2024/01.2025) + **«скидка 30% через Госуслуги»** (отменена с 01.01.2023). Обе ошибки — уверенно поданные **устаревшие факты**. Поймал только strict-factchecker, и только потому что Антон сам попросил «стрикт фактчек». Без его запроса ушли бы неверные цифры.
- **Корень:** `stop-hallucination-detect.sh` ловит «магические проценты» и vague frequency, но НЕ ловит уверенно названные **устаревшие суммы/пошлины/ставки/налоги/правовые пороги** без верификации в этом turn. Деньги+закон из памяти = я считаю их «известными», хотя они меняются (госпошлины, ставка ЦБ, НДФЛ-льгота, тарифы).
- **Решение:**
  1. Skill `/умнею` (`~/.claude/skills/umneyu/SKILL.md`) — по команде извлекает урок из последней ошибки/коррекции в сессии и закрепляет (правило → хук → memory). Это команда «чтобы ты всегда умнел».
  2. **Кандидат-хук** `stop-stale-fact-guard.sh` (Stop, warn-only) — детект денежных сумм в ₽ + правовой/регуляторный контекст (госпошлина|ставка|налог|штраф|тариф|пошлина|льгота|«по закону»|«ст.»|«НК РФ»|«ФЗ») в ответе ПРИ отсутствии WebSearch/WebFetch в этом turn → инжект `[VERIFY-BEFORE-SEND: денежный/правовой факт без источника]`. Bypass `STALE_FACT_OK=1`. **Не зарегистрирован — ждёт approve Антона** (меняет харнес, нужен рестарт, cherny-tips #9).
- **Урок:** деньги + закон, названные из памяти = по умолчанию **UNCONFIRMED**, проверять источником (WebSearch/WebFetch первоисточник) **ДО** ответа, не после. Особенно: госпошлины, ставка ЦБ, НДФЛ, тарифы, сроки по закону — они датируются и устаревают.
- **Связано:** `quality.md` (Challenge-Self), `finance-data-collection.md` (2+ источника на число), `ndfl-formulas.md` (прецедент: strict нашёл неверную НДФЛ-льготу).

### 21. Список deploy-ссылок без прохождения ролей-тестировщиков (инцидент 2026-05-27, USmile сессия 10e980e4)
- **Проблема:** в конце сессии USmile скинул Антону список master-документов + research/семантика, **БЕЗ прохождения тестов ролями**: factcheck только на VDOOH-research, на 4 master-индекса — НЕ был, content-reviewer/code-reviewer вообще не вызывались. Ссылки указал как **относительные пути** (`clients/usmile/MASTER-*.md`), не как полные clickable URL.
- **Антон 27.05 ~22:00:** «если все сделано, давай скидывай список ссылок... но опять же перед этим роли тестировщиков там по фронту и вообще по всем релевантным тематикам... должен быть подключен и должны пройти тесты, а потом уже только ты мне скидываешь эти все финальные деплой линки, полные конечно, чтобы можно было нажать, перейти, посмотреть».
- **Корень:** правило `~/.claude/rules/deploy-report-template.md` существует с таблицей 15 инструментов (включая роли code-reviewer, ui-visual-validator, factcheck-v2), но НЕТ хука который **блокирует ответ-со-списком-ссылок** до прохождения ролей.
- **Также:** ссылки в ответе пользователю должны быть **полные clickable URL** (https://...), не git-paths и не относительные пути.
- **Решение (3 уровня):**
  1. Перед любым «вот ссылки на X» / «готовый список deliverables» — обязательный internal-чеклист ролей по типу контента:
     - HTML/Frontend → ui-visual-validator + accessibility-checker + playwright 3 breakpoints
     - Markdown/Content → factcheck-v2 + content-reviewer (структура/дубли/ссылки)
     - Python/JS code → code-reviewer + security-review
     - Числа/данные → strict-factchecker или /factcheck (+ источники)
  2. Если deliverable — git-файл (не deployed) → сначала **отрендерить в HTML + deploy на artvision.pro/_priv-<topic>-<date>/** ИЛИ явно объяснить «это git-файл, открой через ваш VSCode/finder» с **полным локальным путём** `/Users/antonk/...`
  3. В финальном ответе:
     - Каждая ссылка = **полный URL** (https://...) или **полный локальный путь** (/Users/...)
     - Перед списком — таблица «Тесты пройдены: factcheck ✅ · content ✅ · ...»
- **Кандидат-хук:** `stop-deploy-links-need-tests.sh` (Stop) — детект в финальном ответе паттернов `vot ссылки|список deploy|finalnyy deploy|готов список|deliverables list|MASTER-` + наличие `.md|.html|.csv` ссылок → проверить в transcript текущей сессии: вызывался ли factcheck/code-reviewer для упомянутых файлов. Если НЕТ → warn `[VERIFY: тесты ролями для X файлов не пройдены]`. Bypass: `DEPLOY_LINKS_OK=1`. **Не зарегистрирован — ждёт approve Антона.**
- **Связано:** `~/.claude/rules/deploy-report-template.md`, `feedback_deploy_url_first.md`, `feedback_two_deploy_links_personal_and_product.md`.
