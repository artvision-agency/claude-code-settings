# Аудит целостности хуков и правил Artvision — 2026-05-30

> Источник: workflow `hook-rule-integrity-audit` (run wf_fe4639a5-7fd), 33 агента, 5.26M токенов, 12 мин.
> Контекст: сессия 72749b60 (дедлок-триада хуков → расширение проверки на всю систему).

## Статистика
- **contracts**: 94
- **cycles_total**: 0
- **cycles_confirmed**: 0
- **orphans**: 9
- **rule_conflicts**: 0
- **silent_fail**: 30

## ⚠️ Надёжность прогона (честно)
- ✅ **Циклы (0 подтверждённых)** — надёжно: lint + agents + adversarial verify сошлись. Дедлок-триада 30.05 уже устранена.
- ✅ **Silent-fail (30)** — надёжно, главная находка.
- ✅ **Orphans (9)** — надёжно, verify прошёл.
- ❌ **rule_conflicts=0 — НЕнадёжно.** 6 из 12 батчей RuleDirectives и ОБА агента RuleConflicts упали (StructuredOutput). Обработано только **48 из 91** правила (358 директив). «0 противоречий» = «анализ не завершён», НЕ «противоречий нет». Перезапустить отдельно.

## Orphan-хуки (9) — решения

| Хук | Guardrail | Решение | Почему |
|-----|:---------:|---------|--------|
| `_disabled_inject-knowledge.sh` | — | **keep-disabled** | Filename carries explicit `_disabled_` prefix = intentionally retired. settings.json (lines 301/304) contains permissions to copy/`rm -f` `inject-knowledge.sh` and to delete `_d... |
| `hook-interaction-lint.sh` | — | **keep-disabled** | Not an event hook — header states `Запуск: bash ~/.claude/hooks/hook-interaction-lint.sh` and it reads settings.json directly, prints a report, exits 1 on cycles. It has no stdi... |
| `post-deploy-qa-smoke.sh` | ✅ | **keep-disabled** | By design NOT a Claude Code hook — its own header distinguishes it from `post-deploy-smoke.sh` (the registered PostToolUse hook, settings.json line 1186): this one is `standalon... |
| `post-ui-agent-strict.sh` | ✅ | **wire** | Real factcheck/anti-hallucination guardrail with a documented precedent and a clean exit-0 soft-reminder design (no blocking risk). NOT registered: the only SubagentStop entry i... |
| `post-websearch-factcheck.sh` | ✅ | **wire** | Factcheck guardrail directly enforcing core.md / quality.md / finance-data-collection.md (2+ sources per number). NOT registered — no PostToolUse WebSearch/WebFetch hook exists ... |
| `pre-design-without-brand-source.sh` | ✅ | **wire** | Brand-correctness guardrail with a costly documented precedent; dependency skill brand-extraction exists. NOT registered. Partially overlaps the registered pre-kp-brand-extract-... |
| `pre-scp-medical-aggregator.sh` | ✅ | **keep-disabled** | Its governing rule is retired: the referenced ~/.claude/rules/medical-kp.md exists only as `medical-kp.md.disabled` (the rule was intentionally turned off). The dependency aggre... |
| `save_session.py` | — | **keep-disabled** | Not a hook at all — it reads its payload from sys.argv[1], not from the stdin hook-protocol JSON, and has no Claude Code event semantics (prints help when invoked bare, as a hoo... |
| `stop-smoothing-check.sh` | ✅ | **wire** | Core no-smoothing guardrail and the broken half of a producer/consumer pair: the CONSUMER start-smoothing-report.sh IS registered (settings.json SessionStart, line 387) but this... |

---

Confirmed: settings.json references 185 hooks but my candidate-wire hooks (post-ui-agent-strict, post-websearch-factcheck, stop-smoothing-check, pre-design-without-brand-source, pre-scp-medical-aggregator) are NOT among them — verifying the orphan claims hold. Note `inject-knowledge.sh` IS referenced (permissions, per the orphan analysis). My verification matches the input data. Final synthesis below.

---

# ЧТО ДАЛЬШЕ — дорожная карта целостности логики хуков/правил

Контекст-якорь: 0 подтверждённых циклов блокировки (слой 2 уже ловит их). Реальная боль — **30 fail-OPEN silent-fail-путей**, из которых критичны те, что молча отключают guardrail именно в момент когда он нужен. Решаем СТРУКТУРНО (строгость, не ослабление).

## 1. КРИТИЧНОЕ сейчас (чинить первым)

Severity по принципу «guardrail молча пропускает ровно тот инцидент, ради которого создан».

1. **[P0 / DATA-LOSS] `pre-strip-script-guard.sh` — fail-open на источнике команды.**
   - Читает CMD только из `CLAUDE_BASH_COMMAND`/`TOOL_INPUT_COMMAND` env. Если харнес даёт `tool_input` через stdin (как большинство хуков инвентаря) → `CMD` пуст → `[ -z $CMD ] && exit 0` → strip/clean-скрипт без `--dry-run` проходит. Это ровно ant-partners 157-секций.
   - **Фикс:** добавить чтение stdin JSON как fallback (`jq -r '.tool_input.command // empty'`), затем env. Если оба пусты при matcher=Bash → НЕ exit 0, а fail-CLOSED (exit 2 с явным «не смог распарсить команду»). Регресс-тест: stdin-only payload должен блокировать `python strip_x.py` без dry-run.

2. **[P0 / FINANCE] `pre-finance-deploy.sh` — fail-open при пропавшем factcheck-скрипте.**
   - `set -uo` без `-e`. Если HTML не найден ИЛИ `factcheck-numeric.py` (L5) ИЛИ `factcheck-finance-domain.py` (L6) отсутствуют по хардкод-пути `.claude-shared/scripts` → exit 0 / `DOMAIN_OK=1`. Перемещённая папка скриптов = банковский документ деплоится без numeric/domain-проверки.
   - **Фикс:** «missing dependency = fail-CLOSED» — если обязательный factcheck-скрипт не найден, блокировать deploy (exit 2) с сообщением «factcheck-numeric.py отсутствует, не могу гарантировать проверку». То же для `pre-cleanup-tokens-check.sh-deps` класса (см. ниже).

3. **[P0 / OUTBOUND] `pre-outbound-gate.sh` — нет `set`, fail-open на parse + НЕТ env-bypass.**
   - Единственный un-bypass-able outbound-гейт, но: парс CMD через `python3 ... 2>/dev/null` → при сбое CMD пуст → `[ -z CMD ] && exit 0` молча пропускает scp/email/telegram на чужой хост. То есть «строгий» гейт фейлит-open на кривом вводе.
   - **Фикс:** `set -uo pipefail`; парс-ошибка → fail-CLOSED (exit 2). Bypass НЕ добавлять (см. §5 — владелец отверг).

4. **[P0 / OAUTH-WIPE] `pre-cleanup-tokens-check.sh` — таймаут find = «токенов нет».**
   - `found=$(timeout 4 ... || true)`; на медленной ФС find (`maxdepth 6` по многим danger-dirs) таймаутит → found пуст → «токенов нет → exit 0» → деструктивный `rm` проходит даже когда токены есть. Плюс `grep -oE` не ловит quoted/globbed цели `rm`. Это guard против `rm -rf ~/.npm`.
   - **Фикс:** таймаут find = НЕ «чисто», а fail-CLOSED (блок + «не успел проверить токены, повтори»). Расширить парс целей `rm` на кавычки/globs.

5. **[P1 / KP-FACTCHECK] `pre-scp-kp-strict-factcheck.sh` — exit 1 вместо exit 2.**
   - Python `sys.exit(1)` когда нет свежего strict-report, но PreToolUse БЛОКИРУЕТ только на exit 2. То есть «strict factcheck перед scp КП» де-факто warn-only — слабее заявленного. Совпадает с self-corrections #18.
   - **Фикс:** заменить `sys.exit(1)`→`sys.exit(2)` на пути «нет свежего отчёта». Invalid JSON → тоже fail-CLOSED, не `sys.exit(0)`.

6. **[P1 / STRUCTURAL] класс «внешний скрипт пропал → guard выключился молча».**
   - `pre-finance-deploy.sh`, `pre-scp-dashboard-fns-check.sh`, `pre-deploy-claim-vs-artifact.sh`, `pre-deploy-coords-verify.py` (Nominatim network-fail = PASS). Общий паттерн: дефолт CRITICAL/result → passing при ошибке внешней зависимости/сети.
   - **Фикс (общий принцип):** ввести единый helper `require_dep_or_block()` — отсутствие/ошибка обязательной зависимости = exit 2. Сетевой fail у coords-verify = fail-CLOSED (блок с «не смог геокодировать, проверь пин вручную»), не тихий PASS.

7. **[P1 / DEPLOY-URL] `stop-deploy-url-check.sh` — единственный блокирующий Stop, fail-open на parse.**
   - `python3 ... 2>/dev/null` сбой → SESSION_ID пуст → exit 0. Парс-сбой молча пропускает enforcement «URL первой строкой».
   - **Фикс:** парс-ошибка → сохранять enforcement (повторить парс альтернативным способом / fail с warn-видимым, не тихий exit 0).

**Сквозной корень всех P0/P1:** (а) env-vs-stdin рассинхрон чтения tool_input, (б) `set -uo` без `-e` + `2>/dev/null` → fail-OPEN по умолчанию, (в) хардкод-пути (`-Users-antonk`, `.claude-shared/scripts`) ломаются на других аккаунтах. Это три структурных дефекта, которые надо чинить как ШАБЛОН, а не по одному.

## 2. Orphan-guardrails — действия (конкретные имена)

**WIRE (зарегистрировать — это рабочие guardrail без блок-риска):**

1. **`stop-smoothing-check.sh` → register под `Stop`.** Producer/consumer пара сломана: consumer `start-smoothing-report.sh` УЖЕ в settings.json (SessionStart, line ~387), а producer не зарегистрирован → `smoothing-reports/` всегда пуст → no-smoothing.md не работает. Зависимость `scripts/smoothing-detector.py` существует. Закрывает петлю. **Высший приоритет среди wire** — это ядро no-smoothing.
2. **`post-websearch-factcheck.sh` → register под `PostToolUse` matcher `WebSearch|WebFetch`.** Прямо энфорсит core.md/quality.md/finance-data-collection.md (2+ источника на число). Non-blocking, валидный additionalContext JSON. Класс self-corrections #18.
3. **`post-ui-agent-strict.sh` → register под `SubagentStop` (или `PostToolUse` Agent).** Анти-галлюцинация после UI-субагента (прецедент: выдуманный рейтинг 3.8 для «Шамир»). Exit-0 soft-reminder, нулевой блок-риск. Bypass `UI_STRICT_OFF=1` встроен. Текущий единственный SubagentStop роутит только на agents-office passthrough — добавить вторым.
4. **`pre-design-without-brand-source.sh` → register под `PreToolUse` matcher `Edit|Write|MultiEdit`, НО с проверкой scope.** Прецедент USmile (4 часа бирюзовых макетов для red-white бренда). Шире чем зарегистрированный `pre-kp-brand-extract-check.sh` (покрывает ideas/landings/signage/mockups). **Перед wire — confirm что scope не даёт double-block на KP-файлах** (оба сматчат KP). Bypass `BRAND_SOURCE_OK=1` есть. Приоритет ниже трёх верхних — требует проверки overlap.

**KEEP-DISABLED / DELETE (не трогать или удалить):**

5. **`pre-scp-medical-aggregator.sh` → keep-disabled.** Управляющее правило `medical-kp.md` ретайрнуто (есть только `medical-kp.md.disabled`). Wire воскресил бы выключенный workflow и заблокировал бы медицинские КП. Не регистрировать пока `medical-kp.md` не вернут.
6. **`_disabled_inject-knowledge.sh` → keep-disabled / safe to delete.** Префикс `_disabled_` = намеренно ретайрнут; settings.json содержит permissions на `rm -f inject-knowledge.sh`. Вся knowledge-system выключена осознанно. Не wire. Можно удалить файл для чистоты (низкий приоритет).
7. **`hook-interaction-lint.sh` → keep как standalone (НЕ event-hook).** Это анализатор конфига (читает settings.json, печатает отчёт, exit 1 на циклах), нет stdin-протокола. Правильно незарегистрирован. → идёт в §4 как pre-commit gate, не как event-hook.
8. **`post-deploy-qa-smoke.sh` → keep-disabled.** Вызывается из deploy-скриптов с позиционными аргументами, несовместим со stdin-протоколом. PostToolUse-путь уже покрыт `post-deploy-smoke.sh`.
9. **`save_session.py` → keep-disabled.** Не хук (argv, не stdin). Ручной лог-хелпер.

## 3. Противоречия правил — топ-5

Во входных данных `contradictions` агрегировано как 1 (PreToolUse), детализации нет. Но структурно противоречия УЖЕ устранены принципом владельца «строгость, не bypass». Топ-5 для явного разрешения (по приоритету):

1. **`pre-strip-script-guard.sh` (data-loss блок) vs `core.md`/`antipatterns.md` (strip-скрипты разрешены с dry-run).** Разрешение: hook fail-CLOSED при невозможности доказать `--dry-run`. Правило и хук сходятся только если хук реально читает команду (см. §1.1).
2. **`pre-outbound-gate.sh` (нет bypass) vs остальные блок-хуки (все имеют `*_SKIP/_OK`).** Несогласованность escape-политики. Разрешение: оставить outbound БЕЗ env-bypass (владелец: строго), но добавить в `missing_bypass`-контракт явную метку «intentionally un-bypassable» чтобы lint не флагал как дефект.
3. **`pre-commit-check.sh` (нет bypass) vs `pre-push-qa-check.sh` (`QA_SKIP=1`).** Два QA-гейта с разной политикой обхода для flaky-тестов. Разрешение: НЕ добавлять bypass в commit-check (строгость); вместо этого документировать что flaky-тест чинится, а не обходится. Согласовать с владельцем — единственный пункт где «нет bypass» создаёт операционное трение.
4. **`medical-kp.md.disabled` vs `pre-scp-medical-aggregator.sh` (на диске, ждёт wire).** Правило выключено, хук-orphan ссылается на него. Разрешение: keep-disabled оба согласованно; не воскрешать частично.
5. **Producer/consumer smoothing пара (`stop-smoothing-check.sh` ⊥ `start-smoothing-report.sh`).** Consumer активен, producer мёртв = логическое противоречие пары. Разрешение: wire producer (§2.1).

## 4. Дорожная карта валидации (последовательность)

Порядок строгий — каждый слой опирается на предыдущий.

1. **Слой 0 (СНАЧАЛА, до всех слоёв) — пофиксить P0/P1 fail-open из §1.** Нет смысла валидировать архитектуру хуков, у которых ядро фейлит-open. Конкретно: stdin-fallback + fail-CLOSED шаблон в pre-strip / pre-finance-deploy / pre-outbound-gate / pre-cleanup-tokens + exit2-фикс в pre-scp-kp-strict.
2. **Слой 1 (rule «хуки без циклов» + «хуки fail-CLOSED»).** Записать правило `~/.claude/rules/hook-integrity.md`: (а) хук читает tool_input из stdin JSON с env-fallback, не наоборот; (б) обязательная зависимость отсутствует → exit 2, не exit 0; (в) блокирующий хук блокирует через exit 2 (не exit 1); (г) нет хардкод `-Users-antonk`/username-путей. Это нормирует шаблон для §1.
3. **Wire orphan-guardrails из §2** (stop-smoothing → post-websearch-factcheck → post-ui-agent-strict → pre-design-without-brand-source с проверкой scope). Делать ПОСЛЕ слоя 1 чтобы новые регистрации сразу соответствовали правилу integrity.
4. **Wire `hook-interaction-lint.sh` в pre-commit gate.** Блокирует ввод циклических matcher='' хуков на этапе коммита settings.json (предотвращение, не лечение). Это прямая реализация «структурно, не bypass». Доп: SessionStart-прогон lint read-only для видимости orphan/cycle.
5. **Слой 3 (skill `/validate-logic`).** Прогон `hook-interaction-lint` + rule-conflict-check + fail-open-scan (grep `&& exit 0` после `[ -z` без stdin-fallback) ПЕРЕД добавлением любого хука/правила. Skill агрегирует слой 1+2 в один чек.
6. **Расширить lint на matcher-specific циклы.** Текущий lint ловит только глобальные matcher='' дедлоки; добавить детект циклов внутри одного matcher (например два PreToolUse Bash требующих взаимоисключающих условий).
7. **Слой 5 (тесты взаимодействия).** Регресс-набор: для каждого исправленного P0 — кейс «stdin-only payload должен блокировать». Для каждого wired orphan — кейс «срабатывает + bypass работает». Подключить к pre-push (есть `pre-push-qa-check.sh`).

## 5. Что НЕ делать (анти-ослабление — отвергнуть как weakening)

1. **НЕ добавлять `*_SKIP/_FORCE/_OK` env-bypass в `pre-outbound-gate.sh`.** Владелец явно отверг per-hook exemptions; outbound на чужие хосты должен требовать file-ack/`--ack-anton`. Env-bypass = дыра в единственном строгом outbound-гейте.
2. **НЕ «чинить» silent-fail добавлением fail-OPEN-обработки исключений** (`|| exit 0`, `2>/dev/null && exit 0`). Это и есть текущий баг. Каждый silent-fail чинится в сторону fail-CLOSED, не «тихо пропустить чтобы не мешало».
3. **НЕ добавлять bypass в `pre-commit-check.sh` для flaky-тестов.** Чинить flaky-тест, не обходить гейт. (Единственное исключение для согласования с владельцем — §3.3, но дефолт = строгость.)
4. **НЕ wire `pre-scp-medical-aggregator.sh` и `_disabled_inject-knowledge.sh`.** Их правила намеренно выключены; wire = воскрешение мёртвого workflow и риск блока медицинских КП.
5. **НЕ решать дедлоки matcher='' хуков расширением whitelist'ов** (например добавить tool X в allow-list block-no-taskcreate). Это ослабляет TaskCreate/recap/skill guardrail. Решение — lint-as-pre-commit-gate (§4.4) + предсказуемый precedence, предотвращающий ввод цикла, а не whitelist-патч постфактум.
6. **НЕ удалять `redundant` хуки только потому что «дублируют».** 5 redundant (PreToolUse) — это defense-in-depth (например двойной factcheck для денег). Redundancy ≠ дефект; убирать только подтверждённый no-op (например `stop-anti-rationalization.sh`, который грепает path-строку вместо содержимого — он реально no-op, его чинить или удалять, но это bug-fix, не «снять дубль»).

**Один файл-итог для следующей сессии:** начинать со Слоя 0 (§1, P0×4 + P1×3) — это и максимальный риск, и блокер для всех остальных слоёв. Slоy 2 (циклы) уже закрыт, дедлоков 0 — туда время не вкладывать.