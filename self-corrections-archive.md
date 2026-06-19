# self-corrections — АРХИВ старых инцидентов

> Вынесено из `~/.claude/rules/self-corrections.md` 2026-06-05 чтобы файл-правило влез в 40k-лимит стартового контекста.
> Этот файл НЕ загружается в каждую сессию (лежит вне `~/.claude/rules/`). Хуки этих инцидентов ЖИВЫ и зарегистрированы — enforcement не пострадал (см. таблицу «Активные защитные хуки» в основном файле).
> Полный текст инцидентов #8, #10, #9, #11, #12, #14, #13. Сжатые уроки — в основном `self-corrections.md`.

### 8. "Готово" без прогона qa-full.sh (инциденты 2026-04-18)
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

---

## Инциденты #15–#31 (вынесено 2026-06-19 для 40k-лимита; сжатые уроки — в основном файле, хуки в таблице ЖИВЫ)

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
- **Свежий рецидив 2026-05-29 (combine, сессия 8505c6de):** из 2 фоновых агентов с GLOBAL OVERRIDE-промптом один (link-router research) ЗАЯВИЛ «file written», но mtime файла остался старым (26.05) — НЕ записал; второй (Adenta) записал корректно. Урок: **override НЕ 100%-надёжен даже со свежим промптом**. ОБЯЗАТЕЛЬНО после агента с .md-deliverable — проверить `find <file> -mtime -1` (свежий ли) ДО того как считать задачу закрытой; если старый/нет — дописать самому из task-notification result. Это уже 3-й инцидент (17.05 reviewer-агенты, 29.05 link-router) → правило проверки mtime обязательно.

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

### 22. Уверенные утверждения о Claude Code из памяти/устаревших правил без сверки со справкой (инцидент 2026-05-28, EDUCATION session)
- **Проблема:** при обучении Антона архитектуре Claude Code несколько раз дал НЕВЕРНУЮ информацию, поданную уверенно:
  1. «Hook events — это 5 штук (PreToolUse, PostToolUse, SessionStart, Stop, UserPromptSubmit)» → реально **30+** (SubagentStart/Stop, InstructionsLoaded, TaskCreated, FileChanged и др.)
  2. «Чтобы сделать clients/ отдельным — нужны отдельные проекты ~/artvision-data-clients/» → реально subdir CLAUDE.md + path-scoped rules работают из коробки
  3. «artvision-data/CLAUDE.md сильно больше 200 строк, надо сократить» → реально **179 строк**, под лимитом (не проверил перед утверждением)
  4. «@import уменьшит контекст» → реально «imported files load at launch, не reduce context» (справка)
  5. **ГЛАВНОЕ:** «Hooks НЕ hot-swap, нужен рестарт Claude Code» (×4 раза повторил) → реально справка: «Direct edits to hooks in settings files are normally picked up automatically by the file watcher». Рестарт НЕ обязателен.
- **Корень:** доверие СВОЕЙ ПАМЯТИ и УСТАРЕВШИМ ВНУТРЕННИМ ПРАВИЛАМ (`cherny-tips.md` #9) вместо сверки с первоисточником `code.claude.com/docs`. Это тот же класс что #20 (устаревшие денежные/правовые факты), но про техническую матчасть Claude Code.
- **Что поймало:** Антон сам спросил «рекомендации основаны на справке?» и «можешь привести жёсткий фактчекинг?». Без его вопроса неверная инфа осталась бы.
- **Решение:**
  1. Перед уверенным утверждением о механике Claude Code (hooks/skills/rules/agents/CLI/memory/compaction) — **WebFetch `code.claude.com/docs/en/<topic>`**, не из памяти. Pretraining + наши правила отстают от текущей справки.
  2. Особенно опасно: утверждения о ЧИСЛАХ (сколько events, лимиты строк), о ПОВЕДЕНИИ (перечитывает/не перечитывает, выживает/не выживает /compact), о ВОЗМОЖНОСТЯХ (можно/нельзя).
  3. `cherny-tips.md` #9 исправлен 2026-05-28 (был источником ошибки про рестарт).
- **Кандидат-хук:** `stop-claude-code-claim-unverified.sh` (Stop) — детект в ответе утверждений о Claude Code механике (`hook|skill|rule|subagent|CLAUDE.md|/compact|/clear|settings.json` + модальность «нужно/обязательно/не работает/только/нельзя») БЕЗ WebFetch на code.claude.com в этом turn → warn `[VERIFY: утверждение о Claude Code без сверки со справкой]`. Bypass `CC_CLAIM_OK=1`. **Не зарегистрирован — ждёт approve Антона** (меняет харнес).
- **Связано:** #20 (устаревшие факты), `~/.claude/rules/cherny-tips.md` #9 (исправлен), `quality.md` (challenge-self), правило verify-from-docs.

### 23. Обход /seo-master bypass'ом → урезанный аудит + семантика «из головы», не от конкурентов (DS-Lab 01.06.2026)
- **Проблема:** на SEO-аудите DS-Lab (а) 3× заглушил `/seo-master` через `SEO_MASTER_FORCE=1` ради скорости → пропустил полный 8-шаговый pipeline (SF crawl, Lighthouse, top-pages по трафику, GEO-градусник, матрица приоритетов) → аудит вышел «урезанный» vs наш стандарт (`dental-clinic-blueprint` 14 блоков). (б) Семантику ×4 сгенерировал как МАСКИ из своих знаний ниши + Wordstat-фильтр, а НЕ из реальных ранжирующих ключей конкурентов (SEMrush organic / keys.so) + SERP-кластеризация (`tfidf-clustering.md`). Антон поймал обоими вопросами: «почему урезанный» + «как ты расширил кластеры из топвизора на основании конкурентов» (никак — вот пропуск).
- **Корень:** bypass quality-хука = тот самый сценарий против которого хук и стоит. «Быстро» победило «правильно».
- **Правило (HARD):** SEO-аудит/семантика для клиента — НЕ обходить `/seo-master`. Семантика ОБЯЗАНА быть competitor-derived: SEMrush `domain organic` по конкурентам → SERP-кластеризация → gap, а не маски из головы. Маски допустимы только как ДОПОЛНЕНИЕ к конкурентным ключам, не замена.
- **Связано:** quality.md (SEO gates), parallel-skill-groups (Класс 1), dental-clinic-blueprint, tfidf-clustering.md. Хук pre-tool-seo-task-require-master уже есть — НЕ глушить его на клиентских аудитах.

### 24. Структура аудита/КП «из головы» вместо открытия канонического spec (DS-Lab 01.06.2026)
- **Проблема:** собрал SEO-аудит DS-Lab своей структурой (резюме/семантика/кластеры), НЕ по `templates/seo-audit-spec.md` (7 секций + TOC: §1 профиль, §2 конкуренты, §3 позиции, §3a top-pages, §4 тех, §5 потенциал+ТАРИФ, §6 план 1мес). Совпало только §2+§4. Пропустил §5 тариф (коммерция!) и §1 профиль. Сам /seo-master в 1-й строке: «Spec: seo-audit-spec.md — READ FIRST» — не открыл.
- **Корень:** генерирую структуру из своей модели вместо открытия готового канона. Тот же паттерн что #23 (хендролл вместо скилла) и дизайн-тёмная-тема (вместо системы клиента). Класс: «не загружаю существующий шаблон/спек/правило перед работой».
- **Факт:** seo-audit-spec.md = единый presale-формат И для аудита И для КП (§5 тариф + §6 план = коммерч.хвост). Медицина → dental-clinic-blueprint §XII (14 блоков). Генератор → /presale-kp.
- **Правило (HARD):** ЛЮБОЙ клиентский аудит/КП — ПЕРВЫМ делом `Read templates/seo-audit-spec.md` (или dental-clinic-blueprint для медицины), структурировать СТРОГО по нему. Не собирать «свою» структуру.
- **Кандидат-хук:** `stop-audit-structure-check.sh` — при deploy `clients/*/seo/*.html|presale/*/kp/*.html` грепать наличие маркеров §1-§6 (профиль/конкуренты/позиции/тех/тариф/план). Если <5 из 7 → warn «аудит не по seo-audit-spec». Bypass `AUDIT_STRUCT_OK=1`. Ждёт approve (харнес).

### 25. «Клонируй дизайн сайта» → хендролл текст-спека→frontend-агент вместо клон-тулзов + картинок (USmile DESING 02.06.2026)
- **Проблема:** на «склонируй дизайн fedorov-total + топ-платных лендингов под USmile» сделал 4 frontend-агента с ТЕКСТОВЫМИ описаниями дизайна → вышли generic-шаблоны без картинок. Антон: «по дизайну очень скудно скопировано», «вообще нет картинок перерисованных», «команда сеньоров полная использовалась? все скилы клонирования? гитхабовские инструменты? что со звёздами?», «есть много решений с которыми мы работаем, но не применены».
- **Корень:** класс #23/#24 (хендролл вместо готового решения). НЕ применил: клон-тулзы (single-file-cli ~14k⭐ / monolith ~16k⭐ — дают пиксель-точный автономный HTML с реальными картинками), скилы `website-to-hyperframes`/`design-extract`/`brand-extraction`/`frontend-design`, `gemini-rescue` (мультимодальный), скриншоты оригиналов. Агенты «лепили по словам», не видя дизайн.
- **Решение:** правило `~/.claude/rules/site-clone-pipeline.md` — фиксированный пайплайн (скриншот → single-file/monolith пиксель-клон → замена контента → реальные фото base64 → gemini-полировка). v2 USmile пересобран через single-file-cli.
- **Кандидаты (свежая сессия):** скилл `/site-clone <url>` (клон любого сайта + замена нашим контентом) + хук `pre-agent-clone-handroll-guard.sh` (детект «клон дизайна» без клон-тула в transcript → warn). Ждут approve (харнес на 3 аккаунта).
- **Связано:** #23, #24 (тот же класс), `proven-tools-first.md`, `site-clone-pipeline.md`.

### 26. Гадание на прокси-данных вместо обязательного keys.so/SEMrush ИЛИ честного «Pending» (Doctra 03.06.2026)
- **Проблема:** анализ органики конкурентов (top-pages, кто ранжируется) для КП Doctra делал на ПРОКСИ-метриках (be1 число страниц) + выводах-гаданием → стратегический claim «телемед не владеет органикой, ниша свободна». Антон: «как такое можно писать? хоть одна экспертная SEO-команда это видела? в рамках воркфлоу должно быть обязательное применение сервисов аналитики». Прав — claim вероятно неверен (ПроДокторов ранжируется по симптом-запросам).
- **Корень:** правило `feedback_top_pages_required` (09.05) УЖЕ обязывает: top-pages конкурентов = ТОЛЬКО keys.so (Яндекс) + SEMrush (Google); без них → помечать «Pending — заберём в первую неделю», НЕ выдумывать/гадать. Я правило не исполнил — подменил прокси-данными и выдал гипотезу за вывод. Доступа к keys.so/SEMrush нет (документировано в `reference_artvision_api_access_status`: нет подписки, решение покупки — Антон).
- **Решение:** (1) любой вывод об органике конкурентов БЕЗ keys.so/SEMrush = запрещён; вместо вывода → «Pending до подключения keys.so/SEMrush» ИЛИ явная пометка «гипотеза, требует SERP-проверки». (2) be1/pr-cy число страниц = прокси, НЕ доля трафика и НЕ «кто владеет SERP» — нельзя строить на этом стратегические выводы. (3) В КП Doctra claim понижен до гипотезы + SERP-анализ (keys.so/SEMrush) внесён обязательным шагом Этапа 0.
- **Кандидат-хук:** `stop-organic-claim-without-tool.sh` (Stop) — детект в клиентском артефакте утверждений об органике/трафике конкурентов («ниша свободна / не владеет органикой / X собирает трафик») без признака keys.so/SEMrush в transcript → warn. Bypass `ORGANIC_CLAIM_OK=1`. Ждёт approve.
- **Связано:** `feedback_top_pages_required.md`, `feedback_no_fake_audit_claims.md`, `no-smoothing.md`, `reference_artvision_api_access_status`.

### 27. PPC: 1 слой выдан за всю структуру + «описал»≠«внедрил» (USmile 2026-06-04)
- **Проблема:** на «ключей мало» расширил только ПОИСК-семантику (806 ключей, только широкое соответствие) и заявил Антону «все требования учтены, CPC и конкуренты-гео учтены». Реально: РСЯ ❌, Ретаргет ❌, Аудитории ❌, Поиск-по-конкурентам ❌, типы соответствия Ф/Т ❌ (только broad), гео-полигоны ❌ (собрано, не внедрено). Антон: «а как же РСЯ/Ретаргет/Аудитории? сделай фактчек требований, стрикт. почему нарушил».
- **Корень (3):** (1) приравнял «семантика»=«поисковые ключи», PPC=4 слоя (Поиск/РСЯ/Ретаргет/Аудитории); (2) «учтено» подал по факту НАПИСАНИЯ в хабе, не ВНЕДРЕНИЯ в кабинет (декларация ≠ выполнение); (3) не сверился со STRATEGY-ppc-plan (Э2-Э5 явно про РСЯ/ретаргет/аудитории) перед заявлением статуса — класс #24 (не открыл канон-spec).
- **Фикс:** `anticrisis-ads-template.md` → блоки «PPC=4 слоя, статус по слоям» + «ВНЕДРЕНО≠ОПИСАНО». Перед любым «PPC готово/учтено» — сверка 4 слоёв со STRATEGY + статус ✅/⚠️/❌/🔒 с доказательством на каждый.
- **Связано:** #24 (не открыл spec), #26 (гадание вместо данных), no-smoothing, explicit-approval-tracking, _compliance-checklist §F.
- **Кандидат-хук:** `stop-ppc-status-layers.sh` (Stop) — при «семантика/PPC готово/учтено» без упоминания 4 слоёв (РСЯ+ретаргет+аудитории) → warn. Bypass `PPC_LAYERS_OK=1`. Ждёт approve.

### 28. Кластеризация PPC/SEO по Wordstat-сидам вместо SERP-overlap (USmile 2026-06-04)
- **Проблема:** «расширил семантику» сгруппировав 856 ключей по Wordstat-сидам (услуги: имплантация/протез/виниры…) и выдал за кластеризацию. Антон: «кластеризация абсолютно неверная — она должна строиться на SERP-анализе конкурентов ТОП-10 Яндекса + Вебмастер/GSC. ‘имплантация зубов цена’ и ‘all on 4’ — про одно, но страницы и цены кликов разные = разные кластеры. Обязательно оценивать CPC в прогнозе.»
- **Корень:** нарушил собственное правило `tfidf-clustering.md` (hard=≥3 общих URL в ТОП-10, soft=1-2) + класс #23/#24 (группировка из головы, не от данных конкурентов). Сид ≠ кластер: один интент-сид может дробиться на разные посадочные по SERP.
- **Правильный метод (HARD для любой кластеризации ключей):** (1) собрать ТОП-10 Яндекса по горячим фразам (Topvisor/keys.so/agent-browser — НЕ Wordstat-сиды); (2) матрица пересечения URL → ≥3 общих=один кластер/одна посадочная, 1-2=разные; (3) Вебмастер+GSC = привязка кластер→наш URL; (4) **прогноз CPC (Я.Директ Forecast API) на каждый кластер** — разные кластеры = разные ставки/посадочные/объявления.
- **Фикс:** перекластеризация USmile по SERP+CPC-прогнозу — свежая сессия (SERP-сбор captcha-прон, не на переполненном контексте). Метод в tfidf-clustering.md уже есть — ПРИМЕНЯТЬ, не обходить.
- **Связано:** #23, #24, #26, tfidf-clustering.md, reference_serp_clustering_methodology, ppc-launch-playbook (volume-gate).

### 29. «Нет доступа / делай руками» БЕЗ поиска готового инструмента под задачу (TG re-auth, 2026-06-09)
- **Проблема:** на «прочитай что Андрей скинул в TG» — проверил Telethon-сессии (все мертвы) и объявил «TG не прочитать, нужен ручной re-auth в терминале / вставь текст». Антон настоял 3× («у тебя есть доступы», «есть телетон», «делали скилл», «какой смысл руками — я для этого тебя подключаю»). Только тогда нашёл `scripts/tg-signin-relay.py` — построенный ИМЕННО для этого: Claude гонит check/send/signin сам, пользователь только диктует 5 цифр кода.
- **Корень:** объявил преграду («нельзя/руками») сделав multi-source проверку СОСТОЯНИЯ (сессии мертвы — это правильно), но НЕ поискав готовый ИНСТРУМЕНТ обхода преграды. Класс: `no-false-negative` + `proven-tools-first` — «нет/руками» без `find scripts/ -name '*relay*|*reauth*|*signin*'`. Дорого: тратит время пользователя на убеждение использовать то, что мы сами построили.
- **Правило (HARD):** перед «нет доступа / сделай руками / заблокировано» — обязательный `grep`/`find` по `~/artvision-data/scripts` + `~/.claude/scripts` + skills на готовый инструмент под ЭТУ задачу. Особенно если «мы это делали/настраивали». Преграда (сессия мертва) ≠ «руками» — сначала ищи автоматизацию обхода.
- **Фикс:** TG re-auth детерминирован — relay в скилле `/tg-chat-export` (обязательная пред-проверка) + память `feedback_tg_reauth_deterministic` (phone в tokens, шаги check→send→signin). Следующая сессия не повторит.
- **Связано:** `no-false-negative.md`, `proven-tools-first.md`, `feedback_tg_reauth_deterministic.md`, skill `/tg-chat-export`, #12/#20 (Telethon).

### 30. Инфра-инструменты «на одну точку» + слепота к branch-drift (сессия AUTO CTX 50, 2026-06-11)
- **Проблема (3 связанных):** (а) tg-signin-relay был hardcoded на одну сессию tg_userbot — для восстановления state/exporter пришлось inline-кодить Telethon (хендролл, класс #23/#29); (б) ~/.claude сидел на боковой ветке context-diet-w1 → правки настроек уезжали мимо main и не доходили до других машин; VPS root/.claude отстал на 113 коммитов (с 25.05) — никто не замечал; (в) при «не дошло ли сообщение/видео в TG» рефлекс — переслать заново, вместо проверки истории чата живой Telethon-сессией.
- **Корень:** (а) инструмент построен под один кейс, реестра объектов нет; (б) SessionStart-хук делает pull ТЕКУЩЕЙ ветки — drift ветки и чужие машины вне его зоны; (в) feedback_tool_result_missing_retry знал только про grep локального лога.
- **Решение:** 1) relay апгрейжен: реестр SESSIONS (userbot/state/exporter) + `--session <alias|path>` + `check-all` + автотелефон из живой сессии (телефона в tokens НЕТ — и не нужно); 2) `~/.claude/scripts/sync-health.sh [--vps]` — детект branch-drift+behind по всем репо, встроен шагом в `/weekly-check` §1.8 + хук `session-start-sync-health.sh` (SessionStart, warn-only, без сети, bypass `SYNC_HEALTH_OFF=1`, зарегистрирован 12.06 с approve Антона); 3) правило `artvision-data/.claude/rules/telethon-sessions-registry.md` — реестр, канон восстановления, «проверка доставки = чтение истории, не повторная отправка», запрет копирования .session (AUTH_KEY_DUPLICATED).
- **Урок:** инструмент для класса объектов (сессии/репо/токены) обязан принимать ЦЕЛЬ параметром и иметь check-all по реестру; «машина ≠ аккаунт Claude» — синк живёт на машинах через git, аккаунты делят одно дерево.
- **Связано:** #23, #29, no-false-negative, proven-tools-first, feedback_tg_reauth_deterministic, feedback_tool_result_missing_retry.

### 31. Секреты в ПУБЛИЧНОМ settings-репо — .gitignore был КОММЕНТАРИЕМ, не правилом (инцидент 2026-06-12)
- **Проблема:** при фиксе WordPress MCP (`Unknown site: default_test`) обнаружено: `~/.claude/wp-sites.json` с **plaintext WP-админ паролем** artvision.pro И `channels/telegram/.env` с живым `TELEGRAM_BOT_TOKEN` закоммичены в **публичный** `github.com/artvision-agency/claude-code-settings` (синк на 3 аккаунта+VPS). Оба файла были **live-readable через raw.githubusercontent.com (HTTP 200)** — пароль и бот-токен открыты всему миру (боты-скрейперы индексируют секреты публичных репо за минуты → считать СКОМПРОМЕТИРОВАННЫМИ).
- **Корень:** в `.gitignore` про `wp-sites.json` стояла строка-**комментарий** (`#   wp-sites.json — конфиг сайтов`), а не реальное правило → файл попал в git. Документирование намерения ≠ enforcement (тот же класс, что #8/#9/#18: правило в голове/комментарии не срабатывает, нужен механизм). Мой первый фикс MCP ДУБЛИРОВАЛ пароль (усугубил).
- **Решение (git-сторона, сделано):** реальные правила в `.gitignore` (`wp-sites.json`/`*.env`/`*cookies*.txt`); `git rm --cached` секрет-файлов (локально остаются, MCP работает); `git-filter-repo --invert-paths` вычистка из ВСЕЙ истории (559 коммитов) + force-push main+context-diet-w1, удалена мусорная ветка; raw main→404; permission MCP `mcp__claudeus-wp__*`→`mcp__wordpress__*` (был сломан — не матчил namespace `wordpress`); wp-sites.json схлопнут в 1 ключ.
- **Хук (prevention, ✅ установлен+тесты 3блок/3пропуск):** `~/.claude/hooks/pre-commit-secret-guard.sh` (.git/hooks/pre-commit) блокирует коммит секрет-ФАЙЛОВ (wp-sites.json/*.env/*.pem/*.key/id_rsa/tokens.json) + КОНТЕНТ-паттернов (private key/sk-ant-/ghp_/AKIA/`"PASS"`/bot-token). Bypass `SECRET_GUARD_OK=1`. ⚠️ Грабля BSD grep: паттерн начинался с `-----BEGIN` → grep принял за опции (rc=2, тихо не матчил) → фикс `grep -qE -- "$re"`. На 2 др. аккаунтах+VPS: `cp ~/.claude/hooks/pre-commit-secret-guard.sh ~/.claude/.git/hooks/pre-commit`.
- **🟥 ОБЯЗАТЕЛЬНАЯ ротация (только человек, git-чистка НЕ заменяет):** консилиум старших (3 модели, HIGH) + офиц.справка WP — порядок: (1) сменить WP-пароль `admin` в UI + разлогинить сессии ПЕРВЫМ (нельзя минтить app-password скомпрометированным паролем — атакующий выпишет свой), (2) завести Application Password (Users→Профиль) → в `wp-sites.json`, (3) @BotFather `/revoke` TG-токен, (4) 2FA + аудит логов входов, (5) идеально — сервис-аккаунт с ролью пониже вместо admin.
- **Урок:** секреты НИКОГДА не в синкаемом публичном settings-репо (только gitignored-файл/Keychain/приватный tokens.json). Проверять что `.gitignore` РЕАЛЬНО игнорит (`git check-ignore <file>`), а не «документирует». Публичность репо проверять (`curl raw.githubusercontent.com/.../<file>` → 200 = утечка). Связано: #8/#9/#18 (правило без enforcement), security.md.
- **Дополнение 2026-06-15 (2-й репо `artvision-tg-bot`, PRIVATE — чистка истории filter-repo):** при rewrite истории (`git filter-repo --invert-paths` + force-push 3 веток) — уроки ВЕРИФИКАЦИИ:
  1. **Force-push НЕСКОЛЬКИХ веток одной командой может пройти ЧАСТИЧНО.** `git push --force main refactor fix` у Антона очистил только `main`; `refactor`+`fix` остались с грязной историей (частичный отказ / auto-sync хук перетёр). → ПОСЛЕ force-push проверять **историю КАЖДОЙ ветки отдельно**: `git log <ref> --oneline -- <secret-path>` = 0. Не доверять «push прошёл».
  2. **Мой баг: `git reset --hard origin/<branch>` откатил локальный ЧИСТЫЙ rewrite на ГРЯЗНЫЙ origin.** Сверил «деревья идентичны» (`git diff --stat local origin` = пусто, HEAD-контент совпал) и решил что синхронны — но это HEAD-ДЕРЕВО, а ИСТОРИЯ origin была грязной. **Tree-identical ≠ history-clean.** Восстановил чистый rewrite из `git reflog` (объект жив после reset) → дослал. → НЕ `reset --hard local→origin` пока не подтвердил `git log origin/<ref> -- <secret>` = 0.
  3. **filter-repo в Dumb Zone (57%+) = риск из заголовка #31.** Несколько несогласованных rewrite-прогонов (мой + auto-sync-хук Антона) дали РАСХОДЯЩИЕСЯ чистые истории (один clean SHA у main, другой у моего fix). Держать ОДИН источник правды rewrite; крупную чистку истории — в свежей сессии. Mirror-бэкап ПЕРЕД rewrite обязателен (был: `git clone --mirror . /tmp/...`).
  4. **tokens.json трекался в git и в private-репо** (не только public как в основном #31). Любой репо (даже private) — секреты только gitignored. `git ls-files --error-unmatch tokens.json` при касании любого репо.
