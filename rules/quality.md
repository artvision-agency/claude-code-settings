# Quality Gates — обязательные проверки + QA + Self-Challenge

> **ЖЁСТКОЕ ПРАВИЛО:** каждый тип задачи имеет обязательный набор инструментов. Пропуск шага = ошибка, которую клиент найдёт за нас.
> Действует с 2026-04-18. Прецеденты: 3 фактчека на КП Roman Mebel находили новые ошибки (2026-03-23); 4 раза подряд «всё готово» без QA → недоверие → переделка (2026-04-18/19).

## Корневые причины прошлых сбоев

1. Агенты `research-analyst` НЕ имеют Bash → не делают HTTP HEAD → не проверяют URL
2. Замена URL «вслепую» — подставлены выдуманные URLs без проверки
3. Скрипты (factcheck-v2.py, qa-full.sh) не вызываются автоматически до деплоя/«готово»
4. Самооценка («код чистый» / «smoke прошёл») ≠ полный QA-прогон

## Gates по типу задачи

### 🗂 Любая задача по `clients/<name>/` (Pre-Task Read Protocol)

| Шаг | Что | Кто | Блокер? |
|-----|-----|-----|---------|
| 0 | Прочитать `clients/<name>/CLAUDE.md` + `patches/*.md` + `context-log.md` + последний `meetings/*.md` | Read | ✅ |
| 0a | Если есть pipeline (`generate_page.py`, `master-template.html`, скрипты в `templates/`) — НЕ создавать HTML вручную | проверка наличия pipeline | ✅ |

**Прецеденты:** ant-partners инциденты 18.02 (production-overwrite, template raw-2026 в проде), 24.02 (content-strip, 157 секций удалено), 28.02 (skipped-pipeline, sidebar-template вместо service-template). Суммарно 29+ страниц переделаны.

**Хук:** `pre-client-work.sh` (PreToolUse Edit/Write/Bash) блокирует если нет `/tmp/claude-client-context-clients-<name>` маркера. Bypass: `PRETASK_FORCE=1`.

### 📄 КП / HTML для клиента

| Шаг | Инструмент | Кто | Блокер? |
|-----|-----------|-----|---------|
| 1. Сбор данных | WebFetch + WebSearch (2+ источника) | Claude | — |
| 2. Генерация HTML | Write/Edit | Claude | — |
| 3. URL-валидация | `factcheck-v2.py --standard` (HTTP HEAD на все ссылки/картинки) | **СКРИПТ** | ✅ |
| 4. Визуальная проверка | Playwright screenshot 3 breakpoints | Claude | — |
| 5. Фактчекинг чисел | Senior-агент с Bash (`code-reviewer` / `general-purpose`) | **Агент** | ✅ |
| 6. Деплой | scp | Claude | — |
| 7. Post-deploy | `curl -sI` на каждый URL в HTML | **СКРИПТ** | — |

**Блокер:** шаги 3 и 5 ОБЯЗАТЕЛЬНЫ перед 6. Без них → НЕ деплоить. Хук `pre-scp-factcheck.sh` блокирует если CRITICAL > 0.

Памятка перед отправкой: `/factcheck <файл>` → VERDICT (FAILED = не отправлять) → исправить CRITICAL → повторить → только после PASS/REVIEW отправлять.

### 🔗 Замена URL в HTML

1. Найти реальный URL (Playwright → `page.evaluate` → собрать img src с сайта)
2. Проверить URL: `curl -sI URL` → 200?
3. Заменить (Edit)
4. Перепроверить (`factcheck-v2.py`)

**ЗАПРЕЩЕНО:** подставлять URL по памяти или по шаблону (resize_cache/iblock/xxx). ТОЛЬКО реальные URL, проверенные HTTP-запросом.

### 🎨 Замена шаблона / CSS-класса в CMS клиента

1. До правки — снять снимок computed styles эталонной страницы (font-family, sidebar width, accent color, ширина hero, padding секций)
2. Бэкап ресурса в VersionX (MODX) ИЛИ через CMS API ДО правки
3. Если template ID меняется — STOP, требовать явный approval
4. После — DOM-сравнение через `/validate-pages` или Playwright `getComputedStyle`

**ЗАПРЕЩЕНО:** менять template ID существующего ресурса MODX (или эквивалент в Bitrix/WP) без approval. Прецедент: ant-partners /nashi-uslugi/ 18.02 (raw-2026 template в продакшене вместо template 12), 28.02 (sidebar-blog-template вместо service-template), 27.02 (CRIT-01..05 шрифты Cormorant/Montserrat заменены на system fonts).

### 📊 Числа в документах клиента

1. Из 2+ источников (WebSearch/WebFetch)
2. Маркировать: CONFIRMED / UNCONFIRMED / WRONG
3. Прямая ссылка рядом с числом
4. Проверить ссылку: `curl -sI` → 200?

### 🕷 SEO-аудит / правка `clients/<name>/seo/*` или `*.html` клиента

| Шаг | Инструмент | Кто | Блокер? |
|-----|-----------|-----|---------|
| 1. Screaming Frog crawl | `sf <url> --output-folder clients/<name>/seo/sf-out` | СКРИПТ | ✅ |
| 2. Lighthouse mobile+desktop | `lhci autorun --collect.url=<url> --upload.outputDir=clients/<name>/seo/lighthouse-<date>` | СКРИПТ | ✅ |
| 3. Я.Метрика+Вебмастер API | `seo-toolkit.py --tools metrika,webmaster` | СКРИПТ | ✅ |
| 4. Чтение CSV/JSON | Read sf-out + lhr-*.json | Claude | — |
| 5. Перед написанием отчёта | свежесть артефактов <7 дней | хук `pre-seo-task.sh` | ⚠️ WARN |
| 6. Перед деплоем HTML | factcheck-v2 на отчёт | СКРИПТ | ✅ |

**Блокеры 1-2-3:** без свежих SF + Lighthouse + API-данных любые SEO-выводы = галлюцинация. Хук `pre-seo-task.sh` (PreToolUse Edit/Write/Bash) предупреждает если данных нет. Bypass: `SEO_FRESH_SKIP=1`.

**Единая обёртка:** `python3 ~/artvision-data/scripts/seo-toolkit.py --url <url> --tools screaming-frog,lighthouse,pagespeed,ssl,w3c,metrika,webmaster --output-folder clients/<name>/seo/<date>/`. Лог запусков — `~/.claude/logs/seo-toolkit.log`.

**Cron-фон:** `~/Library/LaunchAgents/pro.artvision.weekly-sf-lighthouse.plist` гоняет SF+Lighthouse раз в неделю по всем активным клиентам (читает `clients/*/config.yaml`), пишет в `clients/<name>/seo/<date>/`. Можно стартовать вручную: `launchctl start pro.artvision.weekly-sf-lighthouse`.

### 🤖 Выбор агента (нужен Bash → не research-analyst)

| Задача | Bash? | Агент |
|--------|:-----:|-------|
| Фактчекинг URL/ассетов | ✅ | `general-purpose` или скрипт |
| Фактчекинг чисел | ✅ | `code-reviewer` / `general-purpose` |
| Анализ конкурентов | ⚪ | `research-analyst` |
| Деплой на VPS | ✅ | `general-purpose` / `devops-engineer` |
| SEO аудит | ✅ | `seo-analyzer` |
| Код-ревью | ⚪ | `code-reviewer` |
| Визуальная проверка | ✅ | `ui-visual-validator` |

## QA Enforcement — НИКОГДА не говорить «готово» без прогона

Перед ЛЮБОЙ из фраз — **ОБЯЗАТЕЛЬНО** прогнать `qa-full.sh` проекта:
«фича готова», «всё работает», «можно закрывать сессию», «готов(о) к деплою», «production-ready».

Если `qa-full.sh` возвращает FAIL → запрещено использовать выше фразы. Вместо них — честно: «PASS X/N, FAIL Y: <список что сломано>».

| Проект | Путь к qa-full.sh |
|--------|-------------------|
| artvision-tg-bot | `vps-bot/scripts/qa-full.sh` (syntax + unit + static security + VPS deploy + E2E smoke) |
| artvision-data | `scripts/qa-full.sh` (shell hooks + knowledge/ + wiki + ai-evolve + memory lint + decisions/ + git state, 85 checks) |
| devops-agent | TODO |

Hook `~/.claude/hooks/pre-push-qa-check.sh` блокирует `git push` если qa-full.sh существует и FAIL.

**Антипаттерны:**
- ❌ «Smoke test прошёл — готово» → прогнать qa-full.sh → PASS → тогда «готово»
- ❌ «Код чистый, синтаксис OK — готово» → unit + integration + E2E тоже нужны
- ❌ «Security-агент прошёл по коду — готово» → PoC эксплойтов в реальной среде + qa-full.sh
- ❌ «На локалке работает — в прод» → VPS deploy check в qa-full.sh должен пройти

История инцидентов (2026-04-18..19): 4 раза «готово» без QA → security агент находил CRIT блокеры, 10% стресса, нет E2E, нет integration, smoke реального коммита поймал fork failure. Если правило нарушено — записать в `self-corrections.md` и добавить проверку в qa-full.sh.

## Challenge-Self — автоматический скептик против галлюцинаций

**Проблема:** Claude генерит «магические числа» («30-40%», «обычно», «в среднем») без источников. Антон замечает руками. Kickoff (BluMart SERM 2026-04-18): сказал «30-40% отзывов с брендами на ЯК» → оказалось 15-20%.

**Pipeline:**
1. Stop-хук `stop-hallucination-detect.sh` парсит ответ на regex-флаги: `magic_percent` (`\d+[-–]\d+%`), `vague_frequency` («обычно», «как правило», «в среднем», «большинство»), `confident_no_source` («работает так», «это факт», «исследования показывают»), `recommendation_pct` («рекомендую X%» без URL).
2. Найдено → пишет `/tmp/self-challenge-needed.json`.
3. UserPromptSubmit-хук `inject-challenge-reminder.sh` в следующий turn читает флаг (TTL 15 мин) → инжектит `[SELF-CHALLENGE REQUIRED]`.
4. Claude обязан вызвать Skill `challenge-self`. Субагент-скептик возвращает KEEP / PATCH / REDO.

**Исключения (challenge не нужен):** пользователь сам оспорил («ты неправ», «я не верю») / ответ про код/конфиг/деплой (проверяется тестами) / challenge уже вызывался в turn / ответ <200 символов или навигационный.

Цель: <1 случай «магической цифры без источника» на 10 ответов клиенту/research.

## Уроки 2026-04-22 (Puratos / zakvaski-rus)

### R8. Международные B2B соцсети — искать по шаблону `{brand}_russia` / `{brand}RU`

В КП v1 написали «соцсети пустое поле» → клиент указала: есть `t.me/puratos_russia` (872 подп) и `vk.com/puratos_russia`. Международные бренды локализуют под регион, не под глобальный `@puratos`.

Алгоритм: 4 паттерна `{brand}_russia`/`{brand}RU`/`{brand}_ru`/`{brand}.ru` → TG `t.me/s/{channel}` preview (без клиента, даёт подписчиков и посты) → VK через Playwright (WebFetch блокируется) → IG/LinkedIn прямой fetch. Только если все 4 пусты → «соцсети не найдены» (не «нет»).

### R9. B2B vs B2C — НЕ применять B2C-логику к B2B

В КП v1 раскритиковали отсутствие «B2C-витрины» (WB/Ozon). Puratos — B2B (продаёт пекарням/заводам). Критика «нет витрины на Ozon» для B2B = профессиональная неграмотность, одна из 4 претензий клиента.

Перед аудитом — определить модель: B2B / B2C / B2B2C. Сигналы B2B: «запрос КП», «связаться с менеджером», «для пекарен/заводов», ИНН в реквизитах, нет корзины/цен, минимальный заказ от N тонн. B2B-метрики: lead-to-deal, средний чек контракта, цикл сделки, retention — НЕ ARPU/GMV/корзина. Маркетплейсы для B2B: TIU, B2B-Center, Дистриклуб — НЕ WB/Ozon.

### R10. Критичные точки КП — ручной WebFetch, не доверять субагенту слепо

В сессии 2026-04-22 субагент-факчекер галлюцинировал: придумал дату публикации `safclub` и подписчиков TG `puratos_russia`. Субагент с широким промптом «заполняет» пробелы правдоподобной выдумкой, особенно по непрочитанным ссылкам.

В КП выделить TOP-5 «критичных точек» (цифры/даты/соцсети которые клиент заметит первым). По каждой — ручной WebFetch / `curl -sI` + показ результата в отчёте. Если субагент пишет «данные получены» без URL — считать UNCONFIRMED, перепроверить. Для дат постов — HTML-атрибут `datetime=`/`data-timestamp=`, не текст «3 дня назад».

## Файлы

| Компонент | Путь |
|-----------|------|
| Stop-хук self-challenge | `~/.claude/hooks/stop-hallucination-detect.sh` |
| UserPromptSubmit self-challenge | `~/.claude/hooks/inject-challenge-reminder.sh` |
| Skill | `~/.claude/skills/challenge-self/SKILL.md` |
| Флаг (эфемерный) | `/tmp/self-challenge-needed.json` |
| Лог | `~/.claude/logs/challenge-self.log` |
| QA hook | `~/.claude/hooks/pre-push-qa-check.sh` |

## Связь с другими механизмами

`strict-factchecker` — пост-деплой HTML (другой домен). `crag-research` — если challenge вернул REDO. `feedback_no_smoothing.md` + `feedback_no_hallucinations.md` — работают в паре с challenge-self.
