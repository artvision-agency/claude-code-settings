# PROPOSAL — Консолидация honesty-хуков (Stop) в единый dispatcher

> **Статус:** ПРЕДЛОЖЕНИЕ для ревью Антона. НЕ применено. settings.json и живые хуки НЕ тронуты.
> **Дата:** 2026-05-29
> **Автор:** Claude (субагент анализа)
> **Вердикт round_table:** HYBRID (confidence HIGH) — llama→KEEP_SEPARATE, gpt-oss-groq→HYBRID (dispatcher), qwen3→HYBRID (группировка по стоимости). Все три против монолитного ADOPT_MERGE.

---

## 1. Резюме и рекомендация

**Рекомендация: HYBRID — Orchestrator Dispatcher `stop-honesty-check.sh`.**

Единый Stop-хук-диспетчер, зарегистрированный ОДНОЙ строкой в `settings.json`, который последовательно вызывает 6 автономных под-проверок. Каждая под-проверка сохраняет свой regex/кейс, свой отдельный bypass-env и свои уникальные side-effect'ы. Живые `.sh`-файлы **не удаляются** — dispatcher вызывает их как под-хуки (либо инкорпорирует логику с раздельными bypass).

**Почему HYBRID, а не ADOPT_MERGE (монолит):**
- Раздельные bypass критичны. Один общий bypass убьёт все 6 проверок разом. Сейчас `NO_RULE_CHECK_OK`, `CC_CLAIM_OK`, `FALSE_NEG_OK` отключают только свою проверку — это надо сохранить.
- Разная природа стоимости. 4 дешёвых regex-хука (мгновенные) + 1 LLM-хук (`stop-smoothing-check.sh` → `smoothing-detector.py` запускает `claude -p`, дорого/медленно, async). Монолит затянет каждый Stop и будет жечь деньги. LLM-проверку надо вызывать условно/async.
- Уникальный cross-turn side-effect `stop-hallucination-detect.sh` → `/tmp/self-challenge-needed.json` (читается UserPromptSubmit-хуком в следующем turn) легко сломать при рефакторинге в монолит.
- Два хука используют ДРУГОЙ I/O-контракт (см. §5 «Подводные камни»): `stop-anti-rationalization.sh` читает env `$CLAUDE_TRANSCRIPT` (строка), `stop-smoothing-check.sh` вообще не парсит stdin. Их нельзя «причесать» под общий stdin-JSON без потери поведения.

**Почему HYBRID, а не KEEP_SEPARATE (оставить как есть):**
- Реальный прецедент orphan-хука (self-corrections #18): хук месяц лежал НЕзарегистрированным в settings.json и «тихо не работал». Сейчас 6 раздельных регистраций = 6 точек, где можно забыть/сломать регистрацию. Dispatcher = ОДНА точка регистрации + единый лог/мониторинг.
- При добавлении 7-й honesty-проверки не нужно лезть в settings.json — добавляешь под-вызов в dispatcher.

**Итог:** dispatcher = одна регистрация, но шесть автономных проверок внутри. Закрывает риск orphan-хука БЕЗ потери точечных bypass и БЕЗ затягивания каждого Stop дорогим LLM-вызовом.

---

## 2. Матрица кейс ↔ хук + unique_cases (НЕЛЬЗЯ потерять)

### 2.1 Сводная матрица (из analysis.case_matrix)

| # | Кейс (паттерн) | Ловит хук(и) | Тип |
|---|----------------|--------------|-----|
| 1 | Магические проценты `30-40%` без источника (`magic_percent`) | hallucination | regex |
| 2 | Числа с единицами `500 клиентов`/`N отзывов` (`magic_number`) | hallucination | regex |
| 3 | Vague frequency «обычно/как правило/в среднем/большинство» (`vague_frequency`) | hallucination + smoothing(LLM) | regex+LLM |
| 4 | Уверенное без источника «это факт/доказано/исследования показывают» (`confident_no_source`) | hallucination | regex |
| 5 | Рекомендация процента «оптимально N%» (`recommendation_pct`) | hallucination | regex |
| 6 | «нигде нет правила X / пробел в rules / не зафиксировано» при том что правило есть | claim-no-rule + false-negative | regex+grep |
| 7 | Фразы-отмазки «pre-existing issue/out of scope/works for now/follow-up task» | anti-rationalization | regex |
| 8 | Выдуманный/искажённый факт (число/URL/название/доля/рейтинг) в документе клиенту | smoothing(LLM) + hallucination | LLM+regex |
| 9 | Скрытая неудача сбора данных (агент/API упал → подан как успех) | smoothing(LLM) | LLM |
| 10 | Подмена данных общими словами «лидер рынка» вместо цифр | smoothing(LLM) | LLM |
| 11 | Пропущенное требование ТЗ без объяснения | smoothing(LLM) | LLM |
| 12 | Преуменьшение масштаба проблемы | smoothing(LLM) | LLM |
| 13 | Предположение выдано за факт «скорее всего» где надо «не знаю, проверю» | smoothing(LLM) + hallucination | LLM+regex |
| 14 | Неверная ниша/география/конкуренты клиента (B2B/B2C) | smoothing(LLM) | LLM |
| 15 | Утверждение о механике Claude Code без сверки code.claude.com | cc-claim-unverified | regex |
| 16 | Категоричный негатив «нет/не нашёл/нет доступа» без multi-source поиска | false-negative | regex |
| 17 | False-negative по доступам/секретам «нет токена/нет пароля» поверхностно | false-negative | regex |

### 2.2 UNIQUE_CASES — носитель единственный, при слиянии НЕЛЬЗЯ потерять

| Кейс | Единственный носитель | Что именно сохранить |
|------|----------------------|----------------------|
| Фразы-отмазки/рационализации (#7) | `stop-anti-rationalization.sh` | regex + порог `>2` совпадений. **I/O: env `$CLAUDE_TRANSCRIPT`**, не stdin! |
| Утверждения о механике Claude Code (#15) | `stop-claude-code-claim-unverified.sh` | regex механики + модальность, оба класса; bypass `CC_CLAIM_OK`; флаг `/tmp/cc-claim-unverified-{session}.json`; suppress если в turn был WebFetch на code.claude.com |
| Скрытая неудача сбора данных (#9) | `stop-smoothing-check.sh` (LLM) | вызов `smoothing-detector.py --analyze` |
| Подмена данных общими словами (#10) | `stop-smoothing-check.sh` (LLM) | то же |
| Пропущенное требование ТЗ (#11) | `stop-smoothing-check.sh` (LLM) | то же |
| Преуменьшение масштаба проблемы (#12) | `stop-smoothing-check.sh` (LLM) | то же |
| Неверная ниша/география/конкуренты (#14) | `stop-smoothing-check.sh` (LLM) | то же |
| Категоричный негатив по доступам (#16/#17) | `stop-false-negative-check.sh` | regex neg + suppress если был Grep/Glob/find/cred-get/find-anywhere в turn; bypass `FALSE_NEG_OK`; флаг `/tmp/false-negative-{session}.json` |
| **Cross-turn side-effect** `/tmp/self-challenge-needed.json` | `stop-hallucination-detect.sh` | ОБЯЗАТЕЛЬНО сохранить — читается UserPromptSubmit `inject-challenge-reminder.sh` в следующем turn |
| **grep-по-4-источникам** (rules + artvision-data/rules + memory + skills) | `stop-claim-no-rule-check.sh` | уникальная I/O grep-операция; bypass `NO_RULE_CHECK_OK`; извлечение TOPIC (SEMrush/Topvisor/…) |

### 2.3 Карта bypass-env (ОБЯЗАТЕЛЬНО раздельные)

| Под-проверка | bypass-env (сейчас) | В dispatcher |
|--------------|---------------------|--------------|
| hallucination | (нет) | предлагается `HALLUCINATION_OK=1` (новый, опционален) |
| claim-no-rule | `NO_RULE_CHECK_OK` | сохранить |
| anti-rationalization | (нет) | предлагается `ANTIRAT_OK=1` (новый, опционален) |
| smoothing(LLM) | (нет) | предлагается `SMOOTHING_OK=1` + общий `SMOOTHING_ASYNC` |
| cc-claim-unverified | `CC_CLAIM_OK` | сохранить |
| false-negative | `FALSE_NEG_OK` | сохранить |
| **весь dispatcher** | — | `HONESTY_CHECK_OFF=1` (общий аварийный рубильник, по умолчанию OFF) |

> **Правило:** dispatcher проверяет каждый bypass ОТДЕЛЬНО. Общий `HONESTY_CHECK_OFF=1` — только аварийный, добавлен сверх, не вместо.

---

## 3. ЧЕРНОВИК объединённого хука

Два варианта реализации dispatcher. **Рекомендуется Вариант A (delegation)** — минимальный риск, под-хуки остаются нетронутыми файлами и продолжают работать автономно.

### Вариант A (рекомендуется): dispatcher-делегатор

Не переписывает логику — просто прокидывает stdin каждому живому под-хуку, проверяя его персональный bypass. LLM-проверку запускает в фоне.

```bash
#!/usr/bin/env bash
# ~/.claude/hooks/stop-honesty-check.sh  (ЧЕРНОВИК — НЕ зарегистрирован)
# Единый Stop-dispatcher для honesty-проверок. Одна регистрация в settings.json.
# Делегирует 6 автономным под-хукам, каждый со СВОИМ bypass-env.
# Аварийный общий рубильник: HONESTY_CHECK_OFF=1 (по умолчанию выкл).
#
# Под-хуки остаются нетронутыми (продолжают работать и автономно при желании).
# Side-effect /tmp/self-challenge-needed.json и /tmp/*.json сохраняются их кодом.

set -uo pipefail
[ "${HONESTY_CHECK_OFF:-0}" = "1" ] && exit 0

H="$HOME/.claude/hooks"
STDIN_JSON="$(cat 2>/dev/null || echo '{}')"

# systemMessage может прийти от нескольких проверок — собираем и печатаем ОДИН раз.
COLLECTED=""

# --- helper: вызвать stdin-под-хук, собрать его stdout(JSON systemMessage) и stderr(warn) ---
run_stdin_subhook () {
  local script="$1"
  [ -x "$script" ] || return 0
  local out err
  out="$(echo "$STDIN_JSON" | "$script" 2>/tmp/honesty-err.$$ )" || true
  err="$(cat /tmp/honesty-err.$$ 2>/dev/null)"; rm -f /tmp/honesty-err.$$
  # под-хук сам уважает свой bypass-env (NO_RULE_CHECK_OK / CC_CLAIM_OK / FALSE_NEG_OK)
  if [ -n "$out" ]; then
    # ожидаем JSON {"systemMessage": "..."} — извлекаем текст
    local sm
    sm="$(echo "$out" | python3 -c 'import sys,json;
try:
  d=json.load(sys.stdin); print(d.get("systemMessage","") or "")
except Exception: pass' 2>/dev/null)"
    [ -n "$sm" ] && COLLECTED="${COLLECTED}${sm}"$'\n\n'
  fi
  [ -n "$err" ] && COLLECTED="${COLLECTED}${err}"$'\n\n'
}

# 1) hallucination — пишет /tmp/self-challenge-needed.json (cross-turn). bypass: HALLUCINATION_OK
[ "${HALLUCINATION_OK:-0}" = "1" ] || run_stdin_subhook "$H/stop-hallucination-detect.sh"

# 2) claim-no-rule — grep по 4 источникам, stderr-warn. bypass: NO_RULE_CHECK_OK (внутри хука)
run_stdin_subhook "$H/stop-claim-no-rule-check.sh"

# 3) cc-claim-unverified — флаг /tmp/cc-claim-unverified-*.json, systemMessage. bypass: CC_CLAIM_OK
run_stdin_subhook "$H/stop-claude-code-claim-unverified.sh"

# 4) false-negative — флаг /tmp/false-negative-*.json, systemMessage. bypass: FALSE_NEG_OK
run_stdin_subhook "$H/stop-false-negative-check.sh"

# 5) anti-rationalization — ДРУГОЙ I/O: читает env CLAUDE_TRANSCRIPT (строка), не stdin.
#    Сохраняем его собственный контракт. bypass: ANTIRAT_OK
if [ "${ANTIRAT_OK:-0}" != "1" ] && [ -x "$H/stop-anti-rationalization.sh" ]; then
  ar="$("$H/stop-anti-rationalization.sh" 2>/dev/null)" || true
  [ -n "$ar" ] && COLLECTED="${COLLECTED}${ar}"$'\n\n'
fi

# 6) smoothing — LLM (дорого/медленно). По умолчанию ASYNC, не блокирует Stop. bypass: SMOOTHING_OK
if [ "${SMOOTHING_OK:-0}" != "1" ] && [ -x "$H/stop-smoothing-check.sh" ]; then
  if [ "${SMOOTHING_SYNC:-0}" = "1" ]; then
    "$H/stop-smoothing-check.sh" >/dev/null 2>&1 || true   # синхронно (отладка)
  else
    ( "$H/stop-smoothing-check.sh" >/dev/null 2>&1 & ) || true  # async — не тормозит Stop
  fi
fi

# Печатаем собранные warning'и (если есть). Stop-хук НЕ блокирует — только информирует.
if [ -n "${COLLECTED// /}" ]; then
  printf '%s\n' "$COLLECTED" >&2
fi

exit 0
```

**Плюсы A:** под-хуки нетронуты; regex/side-effect/bypass на месте по определению; откат = удалить одну строку из settings.json; smoothing async по умолчанию (не тормозит).
**Минусы A:** двойной вызов python3 на дешёвых хуках (overhead ~50-150 мс суммарно на Stop — приемлемо).

### Вариант B (агрессивный): монолитный python с инкорпорированными regex

Один python парсит transcript один раз, прогоняет все regex-блоки. **НЕ рекомендуется** как первый шаг: высокий риск потерять side-effect/contract. Приведён как референс что именно надо инкорпорировать, если позже захочется убрать overhead:

```python
# Блоки regex, которые ОБЯЗАНЫ попасть 1-в-1 (без изменений):
PAT = {
  # из stop-hallucination-detect.sh:
  "magic_percent":       r"(?<!\d)(\d{1,3}[-–]\d{1,3})\s*%",
  "magic_number":        r"(?<!\d)(\d{1,4})\s*(?:раз|человек|клиент|посетитель|отзыв|заказ|лид)",
  "vague_frequency":     r"\b(обычно|как правило|в среднем|примерно|чаще всего|большинство|как известно|считается|общеизвестно)\b",
  "confident_no_source": r"\b(работает так|это факт|точно знаю|гарантирую|доказано|исследования показывают)\b",
  "recommendation_pct":  r"(рекоменд\w+|оптимально|идеально)[^.]*?\d+\s*%",
  # из stop-anti-rationalization.sh (порог >2):
  "rationalization":     r"(pre-existing issue|out of scope|follow-up task|works for now|will address later|beyond the scope|separate concern|TODO: fix|known limitation that|leaving as-is)",
  # из stop-claim-no-rule-check.sh (триггер) + TOPIC + grep по 4 источникам:
  "no_rule_trigger":     r"(нигде\s+(нет|не\s+упоминается|не\s+упомянуто))|(нет\s+правила)|(не\s+зафиксировано)|(пробел\s+в\s+(rules|правилах|инструкциях))|(в\s+(rules|правилах|инструкциях)\s+нет)|(no\s+rule\s+for)|(rule\s+(missing|absent))",
  # из stop-claude-code-claim-unverified.sh (нужны ОБА класса):
  "cc_terms":            r"\b(hook|hooks|хук|хуки|skill|skills|скилл|subagent|субагент|CLAUDE\.md|settings\.json|/compact|/clear|--resume|path-scoped|PreToolUse|PostToolUse|SessionStart|file watcher|hot-swap)\b",
  "cc_modality":         r"\b(нужно|нужен|обязательн|требуется|не работает|только|нельзя|не подхватыв|не перечит|перечитыва|выживает|не выживает|загружа|require|must|always|never|cannot|reload|restart|рестарт)\b",
  # из stop-false-negative-check.sh:
  "false_neg":           r"(нет доступа|не нашёл|не нашел|не существует|нигде нет|нет токена|нет пароля|нет такого правила|нет правила|пробел в правил|не зафиксировано|такого нет|этого нет у нас|\bnot found\b|\bno such\b|doesn't exist|does not exist)",
}
# Side-effect ОБЯЗАТЕЛЬНО воспроизвести: /tmp/self-challenge-needed.json (hallucination),
# /tmp/cc-claim-unverified-{session}.json, /tmp/false-negative-{session}.json.
# Suppress-условия ОБЯЗАТЕЛЬНО воспроизвести: WebFetch code.claude.com в turn (cc),
# Grep/Glob/find/cred-get/find-anywhere в turn (false_neg), URL в тексте, len<порог.
# LLM-часть (smoothing) — отдельным async-вызовом smoothing-detector.py.
```

> **Решение для ревью:** начать с Варианта A. Перейти к B только если замеры покажут заметный overhead на Stop.

---

## 4. Тест-план (мин. 2 кейса на под-проверку: триггер + не-триггер, + bypass)

Прогон ДО любой замены. Скрипт: эмулировать stdin `{"transcript_path": "<fake.jsonl>", "session_id": "test"}` с подготовленным last-assistant текстом; для anti-rationalization — экспортировать `CLAUDE_TRANSCRIPT`.

| # | Под-проверка | Триггер-кейс (должен флагать) | Не-триггер (должен молчать) | Bypass-тест |
|---|--------------|-------------------------------|------------------------------|-------------|
| 1 | hallucination magic_percent | «конверсия выросла на 30-40%» (без URL) → флаг + `/tmp/self-challenge-needed.json` создан | «конверсия 32% (источник: https://…)» → нет флага (URL снимает high) | `HALLUCINATION_OK=1` → файл НЕ создан |
| 2 | hallucination vague | «обычно клиенты берут пакет Рост» → флаг | «по данным GA4 за апрель…» → молчит | — |
| 3 | hallucination magic_number | «привели 500 клиентов» → флаг | «привели 500 клиентов (CRM-отчёт, 2026-05)» — короткий <200 симв → молчит (порог длины) | — |
| 4 | claim-no-rule | «в rules/ нет правила про SEMrush» + TOPIC=SEMrush найден grep'ом → stderr-warn со списком файлов | «правило про SEMrush в kp-brand.md» (нет триггер-фразы) → молчит | `NO_RULE_CHECK_OK=1` → молчит |
| 5 | claim-no-rule TOPIC=none | «нигде нет правила про это» (нет CAPS-tool) → TOPIC пуст → молчит (не паниковать) | — | — |
| 6 | anti-rationalization | `CLAUDE_TRANSCRIPT` с 3× «out of scope/works for now/pre-existing issue» → warn (>2) | текст с 1 «out of scope» → молчит (порог >2) | `ANTIRAT_OK=1` → под-хук не вызывается |
| 7 | cc-claim | «hooks нужно перезапускать, restart обязателен» (нет WebFetch docs) → systemMessage + флаг | «hooks подхватываются file watcher (code.claude.com/docs/…)» → молчит (есть ссылка) | `CC_CLAIM_OK=1` → молчит |
| 8 | cc-claim suppress-fetch | тот же триггер-текст, НО в turn был WebFetch на code.claude.com → молчит | — | — |
| 9 | false-negative | «нет токена для X» (без Grep/cred-get в turn) → systemMessage + флаг | «нет токена для X» НО в turn был Grep/find-anywhere → молчит (suppress) | `FALSE_NEG_OK=1` → молчит |
| 10 | false-negative honest | «не найдено в: tokens.json, access.md, memory» → молчит (честно указал где искал) | — | — |
| 11 | smoothing (LLM) | запуск → `smoothing-detector.py --analyze` отрабатывает, отчёт в `~/.claude/smoothing-reports/` | `SMOOTHING_OK=1` → не вызывается | `SMOOTHING_OK=1` → пропуск |
| 12 | smoothing async | по умолчанию (`SMOOTHING_SYNC` не задан) → dispatcher завершается < 1с, LLM крутится в фоне | `SMOOTHING_SYNC=1` → ждёт завершения (для отладки) | — |
| 13 | dispatcher kill-switch | `HONESTY_CHECK_OFF=1` → exit 0 сразу, ни одна проверка не вызвана | без env → все 6 отрабатывают | — |
| 14 | side-effect chain | после hallucination-триггера: следующий turn UserPromptSubmit `inject-challenge-reminder.sh` видит `/tmp/self-challenge-needed.json` → инжектит `[SELF-CHALLENGE]` | флаг не создан → инжекта нет | — |

**Acceptance:** все 14 PASS на dispatcher ДО регистрации в settings.json. Сравнить с baseline (каждый под-хук автономно даёт тот же результат на тех же входах).

---

## 5. Риски слияния + чек-лист безопасной замены

### 5.1 Риски

| Риск | Severity | Митигировано (Вариант A) |
|------|:--------:|--------------------------|
| Один общий bypass убивает все проверки | CRITICAL | НЕТ общего bypass вместо личных; `HONESTY_CHECK_OFF` только аварийный, дополнительный |
| Потеря cross-turn side-effect `/tmp/self-challenge-needed.json` | HIGH | под-хук вызывается as-is → файл пишет его же код |
| Потеря флагов `/tmp/cc-claim-*`, `/tmp/false-negative-*` | HIGH | то же — код под-хуков нетронут |
| Разные I/O-контракты (anti-rat=env, smoothing=no-stdin) причёсаны под общий → поведение сломано | HIGH | anti-rat вызывается БЕЗ stdin (свой env-контракт); smoothing — отдельной веткой |
| Дорогой LLM-вызов в каждом Stop тормозит/жжёт деньги | MEDIUM | smoothing ASYNC по умолчанию; sync только по `SMOOTHING_SYNC=1` |
| Двойной systemMessage от двух проверок на один и тот же текст (#6, #13 в матрице — claim-no-rule ∩ false-negative) | LOW | dispatcher собирает в один stderr-блок; дубль текста допустим (информирование, не блок) |
| Orphan: dispatcher сам не зарегистрирован | MEDIUM | чек-лист §5.2 шаг 4 + grep-проверка регистрации |
| Регрессия из-за рефакторинга | MEDIUM | Вариант A не рефакторит логику; тесты §4 ДО замены |

### 5.2 Чек-лист безопасной замены (выполнять Антону/при approve)

1. **Backup settings.json:** `cp ~/.claude/settings.json ~/.claude/settings.json.bak-2026-05-29-honesty`
2. **Положить dispatcher** `~/.claude/hooks/stop-honesty-check.sh`, `chmod +x`. Под-хуки НЕ трогать.
3. **Прогон тестов §4 ДО регистрации** — все 14 PASS. Зафиксировать вывод в лог.
4. **Сверка baseline:** прогнать те же 14 входов через КАЖДЫЙ под-хук автономно → результат идентичен dispatcher.
5. **Регистрация:** заменить 6 Stop-записей в settings.json на ОДНУ `~/.claude/hooks/stop-honesty-check.sh`. (Либо оставить под-хуки зарегистрированными и добавить dispatcher параллельно на 1 сессию для shadow-сравнения — безопаснее.)
6. **Проверка регистрации:** `grep -c stop-honesty-check ~/.claude/settings.json` == 1; `grep -c 'stop-\(hallucination\|claim-no-rule\|anti-rationalization\|smoothing\|claude-code-claim\|false-negative\)' ~/.claude/settings.json` == 0 (если перенесли) ИЛИ без изменений (если shadow).
7. **JSON-валидность:** `python3 -c "import json;json.load(open('$HOME/.claude/settings.json'))"` → OK.
8. **File-watcher** подхватит правку settings.json автоматически (cherny-tips #9, проверено по справке) — рестарт не обязателен; для 100% — `/clear`.
9. **Smoke в живой сессии:** 1 ответ с «30-40%» → проверить `/tmp/self-challenge-needed.json` создан; 1 ответ «hooks нужен restart» без WebFetch → systemMessage пришёл.
10. **Откат:** `cp ~/.claude/settings.json.bak-2026-05-29-honesty ~/.claude/settings.json` + удалить строку dispatcher. Под-хуки уже на месте — система возвращается в исходное состояние мгновенно.

### 5.3 Что НЕ делать

- ❌ Не удалять живые `.sh` под-хуки (нужны как делегаты + для отката).
- ❌ Не вводить ОДИН общий bypass вместо персональных.
- ❌ Не делать LLM-проверку (smoothing) синхронной по умолчанию.
- ❌ Не применять без прогона тестов §4 и без backup settings.json.
- ❌ Не трогать settings.json до явного approve Антона (данный артефакт — только предложение).

---

## Приложение. Источники

- Исходные хуки: `~/.claude/hooks/stop-{hallucination-detect,claim-no-rule-check,anti-rationalization,smoothing-check,claude-code-claim-unverified,false-negative-check}.sh` (прочитаны 2026-05-29).
- LLM-движок smoothing: `~/.claude/scripts/smoothing-detector.py` (14 KB, существует).
- Регистрация: `~/.claude/settings.json` строки 531/551/611/638/665 (все 6 зарегистрированы Stop).
- Round_table-вердикт: HYBRID, confidence HIGH (llama/qwen3/gpt-oss-groq, master gpt-oss-groq).
- Прецеденты: self-corrections #11/#16/#18/#20/#22; `quality.md` Challenge-Self; `cherny-tips.md` #9 (file-watcher).
