# HANDOVER: ECC continuous-learning-v2 probation (3 этапа)

**Создано:** 2026-04-27 ~16:30 sessionId ce384151
**Контекст к моменту handover:** ~52%
**Решение зафиксировано:** `~/artvision-data/knowledge/infrastructure/hypotheses.md` H17

## Что сделано в этой сессии

1. **Брейншторм** (skill `superpowers:brainstorming`) на запрос Антона о системе детекта повторов промптов с активным предложением автоматизации.
2. **Жёсткий фактчек 3 источника**:
   - Локальный агент: 4665 jsonl сессий (3.7GB) уже есть как data layer; `extract-session-prompts.py` готов; `continuous-learning-v2` была пустой шелухой.
   - Web-агент: нашёл Homunculus, ECC, prompt-coach, disler.
   - round_table (llama+qwen3+gpt-oss-120b): CONDITIONAL вердикт, рекомендация изолированный профиль + 1 неделя probation.
3. **Соц-доказательство (правило Антона) → разворот решения**:
   - Homunculus (humanplane): 365★, **8 commits, 2 contributors, 3 мес без активности, license NULL** → ❌ слабое
   - ECC (affaan-m/everything-claude-code): **168K★, 26K forks, 866 watchers, 170+ contributors, активный 2026-04-26, Anthropic Hackathon Winner** → ✅ сильное
4. **Установка**: `git sparse-checkout` только `skills/continuous-learning-v2` из ECC → `cp` в `~/.claude/skills/continuous-learning-v2/` (старая шелуха в `_archive/continuous-learning-v2-shell-2026-04-27`).
5. **Запись H17 hypothesis** с rollback процедурой.

## Что НЕ сделано (для свежей сессии)

### Этап 1: Активация наблюдения (Week 1, до 2026-05-04)

**Задача:** включить hooks PreToolUse + PostToolUse → начать писать `observations.jsonl`. observer.enabled оставить **false** (только сбор сырых данных, без background-анализа).

**Шаги:**

1. Проверить текущие hooks в `~/.claude/settings.json`:
   ```bash
   python3 -c "import json; d=json.load(open('/Users/antonk/.claude/settings.json')); print(json.dumps(d.get('hooks',{}), indent=2))"
   ```

2. Использовать skill `update-config` для добавления:
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {"matcher": "*", "hooks": [{"type": "command", "command": "~/.claude/skills/continuous-learning-v2/hooks/observe.sh pre"}]}
       ],
       "PostToolUse": [
         {"matcher": "*", "hooks": [{"type": "command", "command": "~/.claude/skills/continuous-learning-v2/hooks/observe.sh post"}]}
       ]
     }
   }
   ```
   ⚠️ **Не перезаписывать** существующие hooks — только append.

3. Проверка что `observe.sh` не падает на текущих хуках:
   ```bash
   echo '{"session_id":"test","tool_name":"Read","tool_input":{}}' | ~/.claude/skills/continuous-learning-v2/hooks/observe.sh post
   ```

4. После 1-2 дней работы — посмотреть что реально пишется:
   ```bash
   find ~/.claude/homunculus -name "observations.jsonl" -exec wc -l {} \;
   tail -5 ~/.claude/homunculus/projects/*/observations.jsonl
   ```

5. **Метрика 1/3:** instincts.count > 0 после 20+ промптов в `artvision-data` проекте.

### Этап 2: Запуск observer + первый /evolve (Week 2, до 2026-05-11)

**Задача:** включить background-анализ, проверить релевантность кластеризации.

**Шаги:**

1. `vim ~/.claude/skills/continuous-learning-v2/config.json` → `"enabled": true`

2. Запустить observer-loop вручную для теста:
   ```bash
   ~/.claude/skills/continuous-learning-v2/agents/start-observer.sh
   ```
   Логи: `tail -f ~/.claude/homunculus/observer.log` (если файл есть)

3. Через 2-3 дня — `/evolve` команда (она в списке доступных skills):
   ```
   /evolve
   ```
   Должна выдать предложения кластеров → Антон оценивает релевантность.

4. **Метрика 2/3:** ≥1 предложенный skill/command, который Антон одобрит.

### Этап 3: 4 куска кастомной доработки (Week 4, до 2026-05-25)

Дописать поверх ECC только то, чего ECC не покрывает:

1. **Time-window дайджесты** (`~/.claude/scripts/cl2-window-digest.py`):
   - Параметры: `--window 7d|30d|90d|180d`
   - Парсит `~/.claude/homunculus/projects/*/observations.jsonl` за окно
   - Группирует по trigger pattern (sentence-transformers + cosine)
   - Output: markdown в `~/.claude/automation-proposals/<date>-<window>.md`

2. **SessionStart короткое уведомление** (`~/.claude/hooks/start-cl2-proposals-alert.sh`):
   - Читает свежие proposals (за последние 7д)
   - Если есть с confidence>0.7 → инжектит **1-2 строки** (не больше!) в session start
   - Соблюдать `feedback_no_learning_logs.md`: НЕ показывать полный отчёт в чате

3. **Skill `/automate-this`** (`~/.claude/skills/automate-this/SKILL.md`):
   - При срабатывании на proposal — диалог:
     - «Какой триггер? (regex/keyword/event)»
     - «Какой результат? (хук/скилл/cron/команда)»
     - «Probation 3 мес — согласен?»
   - Генерит файл (hook/skill/cron) + регистрирует в settings.json
   - Записывает в `~/.claude/homunculus/probation.jsonl`

4. **Probation tracker** (`~/.claude/scripts/cl2-probation-stats.py`):
   - Поля: `created_at, type, trigger, fired_count, accepted_count, rejected_count, false_positive_count, decision_at`
   - Через 90 дней — auto-promote (если accepted/total > 0.7) или auto-archive

5. **Метрика 3/3:** ≥3 принятых автоматизации, ≤1 false positive за месяц → promote H17 в `rules.md`

## Rollback (если probation провалится)

```bash
# Откатить установку
mv ~/.claude/skills/continuous-learning-v2 ~/.claude/skills/_archive/cl2-rollback-$(date +%Y-%m-%d)
mv ~/.claude/skills/_archive/continuous-learning-v2-shell-2026-04-27 ~/.claude/skills/continuous-learning-v2

# Удалить hooks из settings.json (через update-config skill)

# Очистить данные
rm -rf ~/.claude/homunculus/

# Зафиксировать в H17: "Откачено YYYY-MM-DD по причине X"
```

## Условия rollback

- observations.jsonl растёт >10MB/неделя без полезных инсайтов
- false_positive rate >30% (предлагает мусор)
- Конфликт с существующими хуками
- Производительность Claude Code деградирует (>200ms на промпт)
- Антон субъективно: «шум, не помогает»

## Антипаттерны (НЕ делать)

- ❌ Включать observer.enabled=true в этой же сессии что и hooks (нет данных для отладки)
- ❌ Дописывать 4 куска ДО Week 4 — observations.jsonl должен накопиться
- ❌ Показывать learning логи в чате (см. `feedback_no_learning_logs.md`)
- ❌ Удалять `_archive/continuous-learning-v2-shell-2026-04-27` пока H17 не promoted в rules
- ❌ Установить полный ECC plugin (`/plugin install everything-claude-code@everything-claude-code`) — добавит 47 агентов + 182 skills, конфликты с существующими

## Связанные файлы

- `~/artvision-data/knowledge/infrastructure/hypotheses.md` — H17
- `~/.claude/skills/continuous-learning-v2/SKILL.md` — полная документация
- `~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py` — CLI (status/evolve/promote/projects)
- `~/.claude/skills/_archive/continuous-learning-v2-shell-2026-04-27/` — backup пустой шелухи
- `~/.claude/projects/-Users-antonk/*.jsonl` — 4665 jsonl сессий (исторические данные, можно использовать для backfill анализа)
- `~/.claude/scripts/extract-session-prompts.py` — парсер промптов (для будущего time-window скрипта)

## Контекст для следующей сессии

Свежая сессия → `cd ~/artvision-data && cat .claude/handovers/2026-04-27-cl2-probation.md` → выполнять Этап 1.

В первую очередь: skill `update-config` для регистрации hooks. **Не enable observer** в той же сессии что и hooks.
