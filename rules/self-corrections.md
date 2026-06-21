# Самокоррекция — ошибки которые НЕЛЬЗЯ повторять

> Если повторяешь ошибку — ты тупишь. При новой ошибке — ДОПИСАТЬ СЮДА (сжато).
> Полные тексты инцидентов #8–#31 → `~/.claude/self-corrections-archive.md` (не грузится каждую сессию, grep'абельно). Хуки ВСЕХ инцидентов ЖИВЫ — см. таблицу «Активные защитные хуки» ниже.

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

## МЕТА-ПРАВИЛО: инцидент → хук, не «запомню»

Деструктивный инцидент случился — **обязательно создать PreToolUse-хук** с детерминистичной проверкой. Не «запишу в правило» / «буду внимательнее» / «теперь знаю». Причина: правила в md = моя память, в моменте не срабатывает (#8, #9, #18, #31 — правило было, не вспомнил). Хук работает на уровне харнеса.

Алгоритм после инцидента: (1) паттерн (regex по команде/пути/args); (2) `~/.claude/hooks/pre-<thing>-guard.sh` exit 1 + bypass env; (3) зарегистрировать в `~/.claude/settings.json` под matcher; (4) тест 3+ блок / 3+ пропуск / bypass; (5) дописать строку в таблицу ниже. **Регистрация в settings.json — обязательный шаг** (#18: хук лежал unused месяц).

## Сжатые уроки #8–#32 (детали → архив)

- **#33** Ложная тревога «есть дыра/проблема» БЕЗ полной проверки (3× за сессию 20.06: «Forecast=нет метода», «0 групп»=баг запроса Page.Limit>10000, «58 объявл без баннера»=поисковые TEXT_AD картинку не требуют) → ЗЕРКАЛО #32, обратная сторона. Перед заявлением «дыра/не загружено/сломано/0/нет» — проверить контекст ДО конца (тип сущности, лимиты API, норма ли это). Обе стороны: не-false-negative («нет метода») И не-false-positive («есть дыра»). Для кабинета Я.Директа — `scripts/ppc/cabinet-verify.py` (стандартный план-vs-факт аудит: РК/группы/ключи/баннеры-per-кампания/видео/минус-слова/посадочные-200/утечка). Прецедент 20.06, Антон ловил каждую. **4-й раз: «0 видео в кабинете» → видео Ярмолинского ЕСТЬ локально (assets/video-clips/usmile-team-rsya-{16x9,1x1,9x16}.mp4 + 14 yarmolinsky-video/), просто не залиты. Нарушил #33 СРАЗУ после записи → правило в моменте не сработало → НУЖЕН ХУК** (мета-правило). Кандидат `stop-false-claim-without-search.sh` (Stop, warn): детект «0/нет/не загружено/no X/пусто» по ассетам/данным БЕЗ признака find/grep мультиисточник в turn → warn. Bypass `FALSE_CLAIM_OK=1`. ⏳ собрать в СВЕЖЕЙ сессии (в Dumb Zone 20.06 уже 2 битых коммита — не плодить хуки на деградации).
- **#32** «Forecast мёртв → нет метода для CPC» (ошибка ОДНОГО метода выдана за «нет метода») → ошибка/509 одного метода ≠ «нет метода». CPC Я.Директа = `keywordbids.get/AuctionBids` (ВСЕГДА жив, живой аукцион), Forecast v4 мёртв (509 — не трогать). Проверять рабочий метод + есть ли данные уже в кабинете (имплант-ключи USmile уже были там, 367). Класс no-false-negative. KB: `knowledge/services/yandex-direct/gotchas.md`. Прецедент 2026-06-20, Антон поправил.
- **#8** «Готово» без `qa-full.sh` → перед «готово/работает/production-ready» гнать qa-full.sh, показать PASS N/N. Хук `pre-push-qa-check.sh`.
- **#9** TaskCreate пропуск даже при SessionStart-хуке → 2 слоя: `prompt-taskcreate-nag.sh` + `pre-tool-block-no-taskcreate.sh`.
- **#10** Strip/clean без regression-check (157 секций) → `--dry-run` первым, baseline `.section-counts.json`, git stash. Хук `pre-strip-script-guard.sh`.
- **#11** Shorthand «не нашёл» при поверхностной проверке → grep по 4 источникам (memory + jsonl 30д + recaps + skill) ДО «нет». См. `no-false-negative.md`.
- **#12** Telethon session expired без health check → mtime сессии + наличие api_id/api_hash + реальный `is_user_authorized` (см. #20). Re-auth интерактивно.
- **#13** Self-symlinks в hooks/ → ELOOP. Кандидат `pre-symlink-self-loop-guard.sh` + SessionStart-скан.
- **#14** qcomment accept вслепую (деньги за «На проверке») → принимать только если в live / «Опубликован». Guard `_live_match()`.
- **#15** КП с дефолтной палитрой при копировании шаблона → brand-extract (curl+grep #hex/font) с сайта клиента ДО Write КП. Хук `pre-kp-brand-extract-check.sh` (`BRAND_EXTRACT_OK=1`).
- **#16a** Структуры h-tree/деревом вместо списков → `document-list-format.md` (3 уровня) + хук `post-edit-list-check.sh`.
- **#16b** Claim «нигде нет правила X» без полной проверки → grep по 4 источникам (rules×2 + memory + skills). Хук `stop-claim-no-rule-check.sh` (`NO_RULE_CHECK_OK=1`). См. `no-false-negative.md`.
- **#17** Subagents отказываются писать .md отчёты (встроенный CC-reminder) → `subagent-md-output-override.md` + проверять `find <file> -mtime -1` после агента; не записал → дописать самому.
- **#18** Хук в `hooks/` но НЕ зарегистрирован в settings.json → тихо не работает. При добавлении хука — `grep <hook> settings.json`. SessionStart-скан orphan-хуков.
- **#19** Брендинг Artvision на AdvertMed-партнёрские КП → НЕ трогать white-label (`grep -ci advertmed|варикознет >0` = партнёр). Перед bulk на `*/kp/*` — фильтр. `artvision-branding-policy.md`.
- **#20a** «Протухла сессия» как факт без проверки причины → до ответа проверить api_id/api_hash + `git log -S` + реальный `is_user_authorized`. Security-аудиты молча чистят ключи.
- **#20b** Устаревшие денежные/правовые факты из памяти (госпошлина 650 vs 5000) → деньги+закон = UNCONFIRMED, WebSearch/WebFetch первоисточник ДО ответа. Skill `/умнею`. Кандидат `stop-stale-fact-guard.sh` (ждёт approve).
- **#21a** Баннер event-кампании без брендбука выставки → извлекать бренд И клиента И мероприятия (лого/цвета/название лат+кир). Чеклист event: лого×2, даты, место, стенд, промокод.
- **#21b** Список deploy-ссылок без тестов ролями + относит. пути → перед «вот ссылки» прогон ролей по типу контента + полные https:// URL. `deploy-report-template.md`. Кандидат `stop-deploy-links-need-tests.sh`.
- **#22** Уверенные утверждения о Claude Code из памяти → WebFetch `code.claude.com/docs` ДО утверждения (особенно числа/поведение/можно-нельзя). `cherny-tips.md` #9. Кандидат `stop-claude-code-claim-unverified.sh`.
- **#23** Обход `/seo-master` bypass'ом → урезанный аудит + семантика «из головы». НЕ глушить quality-хук на клиентских аудитах. Семантика competitor-derived (SEMrush/keys.so→SERP), не маски.
- **#24** Структура аудита/КП «из головы» вместо канон-spec → ПЕРВЫМ `Read templates/seo-audit-spec.md` (медицина → dental-clinic-blueprint §XII). Кандидат `stop-audit-structure-check.sh`.
- **#25** «Клонируй дизайн» → текст-спека→frontend-агент без картинок → `site-clone-pipeline.md` (single-file-cli/monolith → замена контента → фото base64). Класс #23/#24.
- **#26** Гадание на прокси-данных (be1) вместо keys.so/SEMrush → вывод об органике конкурентов БЕЗ инструмента запрещён → «Pending» или «гипотеза». `feedback_top_pages_required.md`.
- **#27** PPC: 1 слой выдан за всю структуру + «описал»≠«внедрил» → PPC=4 слоя (Поиск/РСЯ/Ретаргет/Аудитории), статус ✅/⚠️/❌/🔒 с доказательством, ВНЕДРЕНО≠ОПИСАНО. `anticrisis-ads-template.md`.
- **#28** Кластеризация по Wordstat-сидам вместо SERP-overlap → ≥3 общих URL в ТОП-10 = кластер; CPC-прогноз на кластер. `tfidf-clustering.md` — применять, не обходить.
- **#29** «Нет доступа / делай руками» без поиска готового инструмента → перед «нельзя/руками» — `find scripts/` + skills на инструмент обхода (TG re-auth = `tg-signin-relay`). `proven-tools-first.md`, `no-false-negative.md`.
- **#30** Инфра-инструменты «на одну точку» + слепота к branch-drift → инструмент класса объектов принимает ЦЕЛЬ параметром + check-all; `sync-health.sh` (хук SessionStart); проверка доставки TG = чтение истории, не повторная отправка.
- **#31** Секреты в ПУБЛИЧНОМ settings-репо (.gitignore был комментарием) → секреты НИКОГДА в синкаемом репо (gitignored/Keychain/tokens.json). `git check-ignore` что реально игнорит; `curl raw.githubusercontent` на утечку. Хук `pre-commit-secret-guard.sh`. Ротация — только человек. Уроки rewrite-истории: force-push нескольких веток может пройти частично (проверять `git log <ref> -- <secret>`=0 на КАЖДОЙ); tree-identical ≠ history-clean; filter-repo — в свежей сессии, mirror-бэкап ПЕРЕД.

## Активные защитные хуки

| Хук | Matcher | Прецедент | Bypass env |
|-----|---------|-----------|-----------|
| `pre-push-qa-check.sh` | Bash | 18.04 — push без QA, 3× security CRIT в проде | `QA_SKIP=1` |
| `pre-vps-git-guard.sh` | Bash | 23.04 — потеря коммита 9973dc3 через `ssh git pull --rebase` | `VPS_GIT_FORCE=1` |
| `pre-tmp-write-guard.sh` | Write+Edit | 23.04 — `/tmp/gen_dental_reports.py` потерян при reboot | `TMP_WRITE_FORCE=1` |
| `pre-cleanup-tokens-check.sh` | Bash | 17.04 — `rm -rf ~/.npm` убил YouTube OAuth (invalid_grant) | `CLEANUP_FORCE=1` |
| `pre-client-work.sh` | Edit+Write | ant-partners 18/24/28.02 — пропуск Pre-Task Protocol → 29 страниц переделаны | `PRETASK_FORCE=1` |
| `pre-strip-script-guard.sh` | Bash | ant-partners 24.02 — strip без regression-check, 157 секций потеряно | `STRIP_FORCE=1` |
| `pre-bash-resource-guard.sh` | Bash | 26.04 — claude упали 2× за 2ч, OOM (free RAM ~42MB, диск 97%) | `RESOURCE_FORCE=1` |
| `pre-bash-topvisor-guard.sh` | Bash | 29.04 — ДВАЖДЫ сжёг 100 RUB: broadcast-фильтр на `checker/go`. Блок: NOT_IN/MATCH%/EXISTS/GREATER-LESS/checker без EQUALS/EQUALS[0]/EQUALS[]. 8/8 PASS | `TOPVISOR_BROADCAST_FORCE=1` |
| `pre-scp-kp-diff.sh` | Bash | 05.05 — АН-НУР 3 итерации (пропущены элементы starclinic при grep-сравнении). Требует `kp-visual-diff.py` перед scp КП | `KP_DIFF_SKIP=1` |
| `prompt-taskcreate-nag.sh` | UserPromptSubmit | 18-19.04 — TaskCreate пропуск при 180 pending (Layer 1) | (auto-disable) |
| `pre-tool-block-no-taskcreate.sh` | PreToolUse `""` | 27.04 — жёсткий блок (Layer 2) | `TASKCREATE_FORCE=1` |
| `pre-tool-recap-goal-check.sh` | PreToolUse `""` | 29.04 — recap «Цель сессии» пустая на первом Edit/Write/Bash | `RECAP_GOAL_FORCE=1` |
| `pre-kp-bred-block.sh` | PreToolUse `Write\|Edit` | 30.04 — 49 CRITICAL в 39 КП (выручка в ₽, UNCONFIRMED в видимом тексте, artvision.pro, фейк-конкурент) | `KP_BRED_OK=1` |
| `pre-client-lexicon.sh` | PreToolUse `Write\|Edit` | lexicon-lint clients/*/presale/*/kp/*: AI/нейросети, бренд, клише. Whitelist служебных | `LEXICON_INTERNAL_OK=1` |
| `pre-tool-cons-vs-swarm-disambiguate.sh` | PreToolUse `Skill` | 17.05 — 21 случай путаницы /cons (думать) vs /swarm (делать). Warn-only | `CONS_SWARM_FORCE=1` |
| `inject-challenge-reminder.sh` | UserPromptSubmit | магические цифры без источника | (auto после Skill) |
| `stop-hallucination-detect.sh` | Stop | детект галлюцинаций в ответе | — |
| `post-edit-list-check.sh` | PostToolUse `Edit\|Write` | 13.05 — h-tree/ASCII-tree/таблицы иерархии в clients/*/plan,presale,reports,kp/*.html. Warn-only | — |
| `pre-deploy-coords-verify.py` | PreToolUse `Bash` | 16.05 IPOTEKA — пин смещён 4 км. Я.Карты coords vs Nominatim OSM, блок >2 км | `COORDS_VERIFY_SKIP=1` |
| `pre-deploy-price-vs-source.py` | PreToolUse `Bash` | 16.05 IPOTEKA — цена 6.1М vs реальная 11.07М (+82%). HTML vs источник | `PRICE_VERIFY_SKIP=1` |
| `pre-deploy-quote-exists.py` | PreToolUse `Write\|Edit` | 16.05 IPOTEKA — выдуманная цитата. Fuzzy 75% «» vs источник | `QUOTE_VERIFY_SKIP=1` |
| `pre-deploy-formula-consistency.py` | PreToolUse `Bash` | 16.05 IPOTEKA — K/мес шапка vs таблица. Блок >10% расхождения | `FORMULA_CONSISTENCY_SKIP=1` |
| `pre-deploy-delivery-date-source.py` | PreToolUse `Bash` | 16.05 IPOTEKA — дата сдачи Q2'26 vs Q1'28. HTML vs сайт застройщика | `DELIVERY_DATE_SKIP=1` |
| `post-banner-stretch-guard.sh` | PostToolUse `Edit\|Write` | 29.05 Avto.World — `object-fit:fill` растяжение людей ×1.78. Детект fill/`100% 100%`. Warn-only | `BANNER_STRETCH_OK=1` |
| `pre-kp-brand-extract-check.sh` | PreToolUse `Write\|Edit` | 11.05 #15 — КП с дефолт-палитрой при копии шаблона. Требует curl на домен клиента в transcript | `BRAND_EXTRACT_OK=1` |
| `stop-claim-no-rule-check.sh` | Stop | 11.05 #16b — «нигде нет правила» без grep по 4 источникам | `NO_RULE_CHECK_OK=1` |
| `pre-commit-secret-guard.sh` | .git/hooks/pre-commit | 12.06 #31 — секреты в публичный репо. Блок секрет-файлов + контент-паттернов | `SECRET_GUARD_OK=1` |
| `session-start-sync-health.sh` | SessionStart | 11.06 #30 — branch-drift, VPS отстал 113 коммитов. Warn-only | `SYNC_HEALTH_OFF=1` |
| `pre-bash-forecast-reminder.sh` | PreToolUse Bash | 20.06 #32 — блок вызова мёртвого Forecast API (509) → тычет в keywordbids/AuctionBids. Тест 7/7 | `FORECAST_OK=1` |
| `post-tool-large-output-guard.sh` | PostToolUse Bash | 21.06 — большой tool-результат (>100KB) оседает в контексте, жрёт токены каждый turn (замер: ответы Lighthouse/SEMrush/Wordstat/Topvisor/Я.Директ до 5.3МБ). Warn: сохрани в файл по каналам (детализацию не терять), в контекст индекс+сводку. Тест 4/4 | `LARGE_OUTPUT_OK=1` |

При добавлении нового хука — **сразу обновить таблицу** + зарегистрировать в settings.json (#18).

## Кандидат-хуки (ждут approve Антона — меняют харнес на 3 аккаунта)

`stop-stale-fact-guard.sh` (#20b) · `stop-deploy-links-need-tests.sh` (#21b) · `stop-claude-code-claim-unverified.sh` (#22) · `stop-audit-structure-check.sh` (#24) · `pre-agent-clone-handroll-guard.sh` (#25) · `stop-organic-claim-without-tool.sh` (#26) · `stop-ppc-status-layers.sh` (#27) · `pre-symlink-self-loop-guard.sh` (#13) · `pre-bulk-kp-modify-advertmed-guard.sh` (#19) · `pre-banner-event-check.sh` (#21a).
