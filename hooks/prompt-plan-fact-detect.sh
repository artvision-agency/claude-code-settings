#!/usr/bin/env bash
# prompt-plan-fact-detect.sh — UserPromptSubmit hook
#
# Детектит запрос «plan/fact / план-факт / сверь цели» и инжектит
# system-reminder «[PLAN-FACT] вызови Skill /plan-fact». Не блокирует.
#
# Архитектура: пара хук+skill (как challenge-self). Хук гарантирует
# срабатывание «когда прошу», skill выполняет анализ.
#
# Bypass: PLAN_FACT_OK=1
# Snooze per-session: touch /tmp/plan-fact-done-{session_id}
# Self-disable: snooze-файл существует
#
# Skill: ~/.claude/skills/plan-fact/SKILL.md
# ТЗ: ~/.claude/handovers/TZ-plan-fact-skill-hook-2026-05-29.md

set -uo pipefail
[[ "${PLAN_FACT_OK:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)

[[ -z "$PROMPT" ]] && exit 0

# Snooze per-session (после первого срабатывания — тихо)
if [[ -n "$SESSION_ID" ]]; then
  FLAG="/tmp/plan-fact-done-${SESSION_ID}"
  [[ -f "$FLAG" ]] && exit 0
fi

PROMPT_LC=$(echo "$PROMPT" | tr 'А-ЯA-Z' 'а-яa-z')

# Триггер: plan/fact в разных написаниях + русские варианты
if echo "$PROMPT_LC" | grep -qE '(plan[ /._-]?fact|план[ /._-]?факт|сверь цели|сверка план.?факт|разбор сессии.*заявил|что заявил.*что реально)'; then
  cat << 'EOF'
[PLAN-FACT]
Запрос на сверку план/факт. ВЫЗОВИ Skill `plan-fact` — это НЕ /itog.
Метод: сверить ВСЕ запросы сессии (и родственных, если просят) с фактом
через РЕАКЦИИ пользователя (переспрос «уверен?/справка?», поправка, повтор =
факт ≠ заявлению). Вывод: таблица + метрика честности + паттерн провалов +
связь с self-corrections.md. Протокол — в SKILL.md.
EOF
  [[ -n "$SESSION_ID" ]] && touch "/tmp/plan-fact-done-${SESSION_ID}" 2>/dev/null || true
fi

exit 0
