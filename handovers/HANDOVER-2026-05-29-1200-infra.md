# Handover: построены plan-fact + защита от слепоты (продолжение infra-backlog)

**Дата:** 2026-05-29 12:00 MSK
**Контекст:** infra (Claude Code config)
**Сессия:** 8505c6de (после /clear от EDUCATION)
**Статус:** завершено (всё закоммичено + push), осталось #3/#4 на свежую сессию
**Предыдущий handover:** `HANDOVER-2026-05-29-1130-infra.md` + `TZ-plan-fact-skill-hook-2026-05-29.md`

## 🎯 Цель сессии

Продолжить backlog из handover — построить HIGH (plan/fact skill+hook) и MEDIUM (защита от false-negative).

## ✅ Что сделано (с файлами)

**#1 — пара `/plan-fact` (HIGH):**
- `~/.claude/skills/plan-fact/SKILL.md` — глубокая сверка запросов сессии ↔ реакции Антона (переспрос/поправка = факт ≠ заявлению). Глубже /itog (тот только recap-чекбоксы)
- `~/.claude/hooks/prompt-plan-fact-detect.sh` — UserPromptSubmit детектор, snooze per-session, bypass `PLAN_FACT_OK=1`
- Тесты `/tmp/test-plan-fact.sh` — 10/10 PASS
- Зарегистрирован в settings.json UserPromptSubmit (группа 0)

**#2 — защита от слепоты (5 слоёв, MEDIUM):**
- `~/.claude/rules/no-false-negative.md` — правило multi-source grep перед «нет»
- `~/.claude/skills/find-anywhere/SKILL.md` — multi-source поиск (доступ/правило/shorthand/факт)
- `~/.claude/credentials-index.md` — карта 8 источников (tokens.json 43 ключа + access.md×9 + memory + 301 jsonl + Keychain + git log -S + .env + config.yaml)
- `~/.claude/scripts/cred-get.sh` — helper 6 источников + `--json`/`--keychain` режимы
- `~/.claude/hooks/stop-false-negative-check.sh` — Stop-детектор «нет/не нашёл» без grep, 7/7 PASS, bypass `FALSE_NEG_OK=1`
- Зарегистрирован в settings.json Stop

Бэкап settings.json: `~/.claude/settings.json.bak-2026-05-29-planfact`

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---|---|---|
| plan-fact = пара хук+skill | только правило | правило не гарантирует (challenge-self образец) |
| порог хука false-negative 30 символов | 50 | короткие «не нашёл» — главный риск, тест ловит |
| `${Q}` вместо `$Q` в cred-get.sh | bare | unbound-variable краш под non-UTF locale на кириллице |
| СТОП перед #3 | делать сейчас | контекст ~45% (Dumb Zone), консолидация хуков честности деликатна — потеря кейсов |

## ❌ Что НЕ сделано (backlog)

- **#3 консолидация 5 stop-хуков честности** (MEDIUM) — НЕ начато. ТЗ секция C. Требует: round_table (tool-adoption-proof) + построчное чтение всех 5 хуков + матрица «кейс↔хук» + сохранить ВСЕ прецеденты. ОПАСНО в Dumb Zone
- **#4 InstructionsLoaded debug hook + тесты 7 orphan-хуков** (LOW)

## 📚 Уроки

- Тесты ловят реальные баги ДО регистрации: порог 50 убивал короткие «не нашёл» (исправлено 30); `$Q` краш на кириллице (исправлено `${Q}`). 2 бага пойманы тестами — verification loop работает
- Хуки честности (plan-fact ловит мои провалы постфактум, false-negative — превентивно) дополняют challenge-self (галлюцинации). Покрытие: галлюцинации + false-negative + само-провалы

## 🔜 Следующие шаги (приоритет)

1. **MEDIUM #3:** консолидация stop-хуков честности — `TZ-plan-fact-skill-hook-2026-05-29.md` секция C. Свежий контекст + round_table обязательны
2. **LOW #4:** InstructionsLoaded hook, тесты orphan-хуков (секция B)
3. Проверить что новые хуки реально срабатывают в живой сессии (file watcher / после /clear)

## 🗺️ Карта файлов

```
~/.claude/
├── skills/plan-fact/SKILL.md           ← новый (HIGH сделан)
├── skills/find-anywhere/SKILL.md       ← новый (#2)
├── hooks/prompt-plan-fact-detect.sh    ← новый, UserPromptSubmit
├── hooks/stop-false-negative-check.sh  ← новый, Stop
├── scripts/cred-get.sh                 ← новый helper
├── credentials-index.md                ← новая карта доступов
├── rules/no-false-negative.md          ← новое правило
├── settings.json                       ← +2 регистрации (бэкап .bak-2026-05-29-planfact)
└── handovers/
    ├── TZ-plan-fact-skill-hook-2026-05-29.md  ← ГЛАВНЫЙ для #3/#4 (статусы обновлены)
    └── HANDOVER-2026-05-29-1200-infra.md      ← этот файл
```

## ⚠️ Гачи

- **Новые хуки** активируются file watcher'ом авто (cherny-tips #9), но для 100% гарантии — `/clear`
- **Security при коммитах в ~/.claude:** НИКОГДА `git add -A` — там tokens/Keychain/venv. Коммитил только перечисленные файлы поимённо
- **#3 НЕ начинать без round_table** — у каждого из 5 stop-хуков свои тесты/прецеденты в self-corrections, слепое слияние = потеря защиты
- Telethon session expired (8 дней) — для TG нужна re-auth (код вводит Антон)

## 🔗 Связанные ресурсы

- ТЗ + backlog: `~/.claude/handovers/TZ-plan-fact-skill-hook-2026-05-29.md`
- Предыдущий: `HANDOVER-2026-05-29-1130-infra.md`
- Класс ошибок: `self-corrections.md` #11/#16/#20/#22
