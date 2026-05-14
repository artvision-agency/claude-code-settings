# Handover: Orchestrator 4x Week 1 — Tasks 3-5 pending

**Дата:** 2026-05-11 19:07 MSK
**Контекст:** products (orchestrator)
**Сессия:** 7dfd1ed1 (предыдущая: 8d1a1030)
**Статус:** в работе, context exhausted на 2%
**Branch:** `feat/orchestrator-week1` в `~/artvision-data`
**Pilot client:** **adenta.pro** (подтверждено Антоном "го")

## 🎯 Цель прошлых сессий

Запустить orchestrator 4x parallel-агентов на основе плана `docs/plans/2026-05-11-orchestrator-4x-week1.md`. Неделя 1: TDD-скрипты cost-audit + session-audit, hook subagent-driven suggester, worktree spawn, pilot skill `/market-audit`.

## ✅ Что сделано (2/5)

### Task 1 — `cost-audit.py` (commit `0380205eb`)
- `scripts/orchestrator/cost-audit.py`
- `tests/orchestrator/test_cost_audit.py` — 8/8 PASS
- Парсит ccusage / Anthropic API usage за период, считает $/токен по модели

### Task 2 — `session-audit.py` (НОВЫЙ коммит, ещё не запушен)
- `scripts/orchestrator/session_audit.py`
- `tests/orchestrator/test_session_audit.py` — 24/24 PASS
- Классификация JSONL-сессий: 9 типов (kp/seo/orm/bot/infra/...)
- Учитывает `custom-title` + первые 5 user-сообщений (не только первое)
- Russian regex без trailing \b (Cyrillic suffixes)
- Aggregate top-N по `(total_minutes, sessions, avg)`
- CLI: `python3 scripts/orchestrator/session_audit.py --days 180 --top 10`

### Реальный вывод за 180 дней (277 сессий, ~2145h)
```
kp     630.5h / 81 sessions / avg 467 min
seo    387.5h / 23 sessions / avg 1011 min
orm    253.8h / 27 sessions / avg 564 min
other  ~650h  / 115 sessions  (микс)
```

**Pilot для Task 5:** Антон подтвердил adenta.pro (КП-категория — max time sink).

## ❌ Что НЕ сделано (3 задачи)

### Task 3 — `worktree-spawn.sh` (TDD)
**Что нужно:** bash-скрипт для изоляции параллельной работы агентов в git worktree.
- Файл: `scripts/orchestrator/worktree-spawn.sh`
- Тесты: `tests/orchestrator/test_worktree_spawn.bats` (если bats есть) ИЛИ `test_worktree_spawn.sh`
- Acceptance: создаёт worktree из current branch, выводит путь, cleanup-флаг `--cleanup`
- Точка старта: смотри план `docs/plans/2026-05-11-orchestrator-4x-week1.md` Task 3

### Task 4 — hook `pre-tool-suggest-subagent-driven.sh`
**Что нужно:** PreToolUse hook для Edit/Write/Bash который при N+ независимых задачах в очереди предлагает использовать `superpowers:subagent-driven-development`.
- Файл: `~/.claude/hooks/pre-tool-suggest-subagent-driven.sh`
- Регистрация: `~/.claude/settings.json` PreToolUse matcher `Edit|Write|Bash`
- Триггер: detect 3+ TaskCreate в активной сессии без Agent вызовов
- НЕ блокирующий — только подсказка (exit 0 + echo на stderr)

### Task 5 — skill `/market-audit` (pilot adenta.pro)
**Что нужно:** Skill для 5 параллельных subagents на market research клиента.
- `~/.claude/skills/market-audit/SKILL.md`
- 5 параллельных Agent (subagent_type=`general-purpose` с Bash+WebFetch):
  1. competitor landscape (top-10 SERP)
  2. ИКС / pr-cy.ru / возраст домена / индексация
  3. NAP + агрегаторы (Я.Карты, 2GIS, Zoon, ProDoctorov для мед)
  4. backlink profile (Semrush snippet)
  5. content gap (TF-IDF top-pages)
- Output: `clients/<slug>/market-audit-YYYY-MM-DD/<5-files>.md` + `summary.html`
- Pilot run: `/market-audit adenta.pro` (медицинская клиника, регион ?)

## 🧠 Решения и почему

| Решение | Альтернатива | Почему |
|---|---|---|
| Tasks 3+4 в параллель (worktree) | sequential | независимые scope, можно делать одновременно |
| Pilot = adenta.pro (а не Творим) | clients из активной MRR | КП = max time sink (630h/81 сессий), adenta уже в TODO для разведки |
| classify по custom-title + first 5 msgs | only first user msg | первый msg часто "продолжи" / hook injection — слабый сигнал |
| Russian regex без trailing \b | full \b...\b | \b после Cyrillic suffix не матчит (отзыв vs отзывы) |

## 📚 Уроки сессии

- `session_audit.py` показал "other" = 650h/115 сессий — нужен расширенный classifier (учитывать tool calls, не только text)
- avg SEO session = 17h — это очень длинные сессии или некорректный duration (last assistant timestamp - first user). Возможно бьются на под-периоды.
- Skill-required hook ловит слова из user message (decision, context, handover) — каскадно блокирует пока не вызовешь каждый. **Сохранить в feedback memory.**

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** Task 3 (worktree-spawn.sh) + Task 4 (hook) в параллель через `Agent`-рой 2 шт
2. **HIGH:** Task 5 (`/market-audit` skill) — после 3+4, чтобы pilot run сразу использовал worktree
3. MEDIUM: запушить feat/orchestrator-week1 в origin (сейчас локальный)
4. LOW: расширить session_audit classifier (учитывать tool calls для "other"-bucket)

## 🗺️ Карта файлов

```
~/artvision-data/ (branch: feat/orchestrator-week1)
├── docs/plans/2026-05-11-orchestrator-4x-week1.md  ← план Task 1-5
├── scripts/orchestrator/
│   ├── cost-audit.py        ← Task 1 DONE
│   ├── session_audit.py     ← Task 2 DONE
│   └── worktree-spawn.sh    ← Task 3 TODO
├── tests/orchestrator/
│   ├── test_cost_audit.py       (8/8 PASS)
│   └── test_session_audit.py    (24/24 PASS)
└── sync/recaps/
    ├── 8d1a1030-...md  (прошлая, Task 2 acceptance закрыт)
    └── 7dfd1ed1-...md  (текущая, sync+handover)

~/.claude/
├── hooks/pre-tool-suggest-subagent-driven.sh  ← Task 4 TODO
└── skills/market-audit/SKILL.md                ← Task 5 TODO
```

## ⚠️ Гачи

- **Branch `feat/orchestrator-week1` не запушен** в origin — Task 2 коммит локальный
- **Context был 2%** в конце сессии → /compact или новая сессия обязательны
- Hook `skill-required` ловит триггерные слова из user-prompts (context/decision/handover/etc) — придётся проходить каждый skill один раз ИЛИ touch `/tmp/skill-required-done-<sessionId>`
- При работе с adenta.pro — это медицинский клиент (стомат-софт), применять `medical-kp.md`: основной регион клиента + 8 мед-агрегаторов
- adenta.pro контекст: ЕЁ задачи уже в TODO (см. session start hook): "Adenta: глубокая разведка сайта", "scan клиник", "оффер-шаблон сайт+онлайн-консультант", "counterparty-check"

## 🔗 Связанные ресурсы

- План: `~/artvision-data/docs/plans/2026-05-11-orchestrator-4x-week1.md`
- Предыдущий recap: `sync/recaps/8d1a1030-f9b4-4825-9401-61bd322418e8.md` (Task 2 closed)
- Текущий recap: `sync/recaps/7dfd1ed1-255c-4dd3-a923-1304e2b1b90a.md`
- Adenta в реестре: НЕТ (новый presale-кандидат, см. session start hook)
