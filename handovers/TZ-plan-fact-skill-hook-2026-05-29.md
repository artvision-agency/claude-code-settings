# ТЗ: plan/fact — skill + hook (построить после /clear)

**Дата:** 2026-05-29
**Контекст постановки:** EDUCATION session, контекст был 416% → отложено на чистую сессию
**Заказчик:** Антон. Запрос: «plan/fact — команда сравнить ВСЕ цели/запросы/вопросы в сессии И родственных предыдущих с фактом выполнения, путём сверки МОЕЙ реакции и вопросов на результаты, + вывод».

## Чем отличается от существующего `/itog`

| | `/itog` (есть) | `/plan-fact` (строим) |
|---|---|---|
| Источник | только recap acceptance-чеклист | весь transcript + recap + родственные сессии |
| Метод | механическая сверка [x]/[ ] | **сверка по реакциям Антона** (переспрос/поправка = факт ≠ заявлению) |
| Охват | текущая сессия | текущая + родственные (по client/cwd/тема) |
| Вывод | COMPLETED/PARTIAL/ABANDONED | **метрика честности** + паттерн моих провалов |

## Архитектура — ПАРА хук+skill (как challenge-self)

Решение Антона: «скорее это хук». Точнее — **хук-детектор гарантирует срабатывание + skill выполняет анализ**. Правило (rule) отвергнуто — не гарантирует (за сессию 3 раза игнорировал правила из памяти).

### Файл 1: `~/.claude/skills/plan-fact/SKILL.md`

Протокол выполнения:
1. Определить sessionId текущей + найти родственные (grep по client-slug / cwd / теме в `~/artvision-data/sync/recaps/*.md` и последних jsonl)
2. Извлечь ВСЕ запросы пользователя из transcript(ов) по порядку
3. Для каждого: что Claude ЗАЯВИЛ (сделано/работает/готово) ↔ РЕАКЦИЯ Антона на следующем шаге
   - переспрос «а ты уверен?» / «основано на справке?» / поправка / повтор запроса = **сигнал факт ≠ заявлению**
   - принял молча / новая тема = заявление подтверждено
4. Таблица: `# | Запрос | Заявление | Реакция Антона | Реальный факт | Вердикт ✅/🟡/❌`
5. Вывод:
   - метрика: X/N запросов где факт=заявлению с первого раза
   - % где Антон вынужден поправить
   - **паттерн провалов** (классифицировать: самоуверенность из памяти / недосказанность / промах scope / ...)
   - связь с self-corrections.md (какой класс ошибки)

Формат: краткий, таблица + вывод. Без воды. (правило document-list-format — структуры списками)

### Файл 2: `~/.claude/hooks/prompt-plan-fact-detect.sh` (UserPromptSubmit)

- regex детект: `plan.?fact | план.?факт | план/факт | сверь цели | сверка план факт`
- если матч → инжект system-reminder: «[PLAN-FACT] Вызови Skill /plan-fact — сверка целей сессии + родственных с фактом через реакции пользователя»
- self-disable после вызова (как challenge-self)
- Bypass: `PLAN_FACT_OK=1`

### Файл 3: регистрация + тесты

- settings.json → UserPromptSubmit
- тесты `/tmp/test-plan-fact.sh`: триггер ловится / не-триггер игнор / bypass работает — мин 5 кейсов PASS ДО регистрации
- коммит + push в claude-code-settings (синк 3 аккаунта)

## Прецедент-демонстрация (уже сделано вручную в EDUCATION session)

Я провёл plan/fact вручную по сессии EDUCATION — нашёл паттерн «самоуверенное утверждение из памяти без проверки», 3 раза за сессию, все ловил Антон фразой-зондом «уверен?/справка?/проверка?». Это эталон что должен выдавать автоматический /plan-fact.

## Связано

- `~/.claude/skills/itog/SKILL.md` — родственный (узкий)
- `~/.claude/skills/challenge-self/` — образец архитектуры хук+skill
- `~/.claude/rules/self-corrections.md` #22 — класс ошибки который plan/fact ловит
- `~/.claude/rules/quality.md` — challenge-self pipeline (тот же паттерн)
- `feedback_compare_goal_vs_result_session_end.md` (memory) — родственное правило сравнения цель↔факт

## Статус: ✅ СДЕЛАНО (2026-05-29, сессия после /clear).
- skills/plan-fact/SKILL.md ✅ · hooks/prompt-plan-fact-detect.sh ✅ (10/10 PASS) · settings.json ✅ · push ✅

---

# Незакрытые рекомендации EDUCATION session (backlog после /clear)

Проверено на диске 2026-05-29. ~70% рекомендаций сделано, 30% отложено.

## A. ✅ СДЕЛАНО (2026-05-29) — защита от «слепоты» (false negative)

Класс ошибки: «не нашёл = нет нигде» (прецедент: avprocontext пароль). 5 слоёв ПОСТРОЕНЫ:
1. ✅ `~/.claude/rules/no-false-negative.md`
2. ✅ `~/.claude/skills/find-anywhere/SKILL.md`
3. ✅ `~/.claude/credentials-index.md` (8 источников, 43 ключа tokens.json)
4. ✅ `~/.claude/scripts/cred-get.sh` (6 источников + --json/--keychain)
5. ✅ `~/.claude/hooks/stop-false-negative-check.sh` (Stop, 7/7 PASS, зарег.)
Всё закоммичено + push.

## B. НЕ сделано — прочее

- InstructionsLoaded hook для дебага (видеть какие правила реально загружены)
- Тесты для 7 orphan-хуков Stage 1 (зарегистрированы, но логика не верифицирована)

## C. Консолидация дублей (round_table перед началом — adopt паттерна)

| Группа | Файлы | Действие |
|---|---|---|
| Stop-хуки честности (5) | stop-hallucination-detect, stop-claim-no-rule-check, stop-anti-rationalization, stop-smoothing-check, stop-claude-code-claim-unverified | 🟡 кандидат: 1 хук `stop-honesty-check.sh` с под-проверками. ОСТОРОЖНО — у каждого тесты/прецеденты в self-corrections, не потерять кейсы |
| Finance-хуки (4) | pre-finance-deploy, pre-finance-no-period-split, post-edit-finance-numbers, pre-agent-finance-context | 🟡 проверить overlap (разные фазы pre-scp/формулы/post-edit/inject — возможно НЕ дубли) |
| itog vs plan-fact | skill itog + skill plan-fact (строим) | 🟡 plan-fact может поглотить itog ИЛИ оставить itog как быстрый, plan-fact как глубокий |
| Правила global↔project | document-list-format, parallel-skill-groups, proven-tools-first, task-routing, asset-capture | ❌ НЕ ТРОГАТЬ — намеренный git-sync дубль на 3 аккаунта |

Метод консолидации (обязательно):
1. Прочитать логику ВСЕХ хуков группы построчно
2. Составить матрицу «какой кейс какой хук ловит»
3. round_table — adopt объединённого паттерна (tool-adoption-proof.md)
4. Объединить с сохранением ВСЕХ кейсов + переписать тесты
5. Прогнать тесты ДО замены в settings.json
6. Backup settings.json перед изменением

## Приоритет backlog (после /clear)
1. HIGH: plan/fact skill+hook (явный запрос Антона)
2. MEDIUM: защита от «слепоты» (5 слоёв, секция A)
3. MEDIUM: консолидация stop-хуков честности (секция C, с round_table)
4. LOW: InstructionsLoaded debug hook, тесты orphan-хуков
