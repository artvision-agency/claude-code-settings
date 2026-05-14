#!/usr/bin/env bash
# stop-session-compare-goal.sh
# Stop-хук: при закрытии сессии напоминает сделать «Сравнение требований с результатом»
# (таблица Критерий | Ожидание | Факт | Статус + вердикт ✅/⚠️/❌)
#
# Установлено: 2026-05-13 после явной просьбы Антона в сессии MIRBIR (4ad36407):
# «хочу в конце сессии всегда делать такие сравнение»
#
# Правило: ~/.claude/projects/-Users-antonk/memory/feedback_compare_goal_vs_result_session_end.md
# Phase 5 /goal: ~/.claude/skills/goal/SKILL.md
#
# Логика:
# 1. Получить sessionId из stdin (JSON tool_input от Claude Code hook system)
# 2. Если есть active recap или goal-файл → проверить наличие «Сравнение с целью» в transcript
# 3. Если не делалось → инжектить мягкое напоминание в stderr (warn, не блокирует)
#
# Bypass: COMPARE_SKIP=1
set -euo pipefail

[[ "${COMPARE_SKIP:-0}" == "1" ]] && exit 0

INPUT=$(cat 2>/dev/null || echo '{}')
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id','') or d.get('sessionId',''))" 2>/dev/null || echo "")

[[ -z "$SESSION_ID" ]] && exit 0

# Найти recap-файл для этой сессии
RECAP="/Users/antonk/artvision-data/sync/recaps/${SESSION_ID}.md"
TRANSCRIPT_DIR="/Users/antonk/.claude/projects/-Users-antonk"
TRANSCRIPT="${TRANSCRIPT_DIR}/${SESSION_ID}.jsonl"

# Если recap отсутствует — сессия скорее всего служебная, пропускаем
[[ ! -f "$RECAP" ]] && exit 0

# Если recap уже CLOSED — не напоминаем
if grep -qE "Status:\s*CLOSED|✅ COMPLETED|❌ ABANDONED" "$RECAP" 2>/dev/null; then
  exit 0
fi

# Если в recap нет цели/критериев — нечего сравнивать
if ! grep -qE "## Цель сессии|## Acceptance criteria|Deliverables" "$RECAP" 2>/dev/null; then
  exit 0
fi

# Проверить goal-файлы в active состоянии
ACTIVE_GOALS=""
if [[ -d /Users/antonk/artvision-data/goals ]]; then
  ACTIVE_GOALS=$(grep -lE "Статус:\s*ACTIVE|Status:\s*ACTIVE" /Users/antonk/artvision-data/goals/GOAL_*.md 2>/dev/null | head -3 || echo "")
fi

# Проверить transcript — было ли «Сравнение» / «Критерий | Ожидание | Факт» в последних reply
COMPARE_DONE=0
if [[ -f "$TRANSCRIPT" ]]; then
  # Последние 30 строк (~5-10 turns) — есть ли упоминание сравнения
  if tail -30 "$TRANSCRIPT" 2>/dev/null | grep -qiE "Критерий.*Ожидание.*Факт|Сравнение с целью|План vs Факт|план / факт|вердикт.*целью|ЦЕЛЬ ДОСТИГНУТА|ЦЕЛЬ НЕ ДОСТИГНУТА"; then
    COMPARE_DONE=1
  fi
fi

[[ "$COMPARE_DONE" == "1" ]] && exit 0

# Инжектим напоминание
cat >&2 <<EOF

🔔 СРАВНЕНИЕ С ЦЕЛЬЮ — рекомендуется перед закрытием сессии

Правило: в конце КАЖДОЙ сессии — таблица «Критерий | Ожидание | Факт | Статус» + вердикт.

Источники критериев (приоритет):
EOF
[[ -n "$ACTIVE_GOALS" ]] && echo "  • Active goal-файлы: $(echo "$ACTIVE_GOALS" | head -1)" >&2
echo "  • Acceptance criteria из recap: $RECAP" >&2
echo "  • Исходный запрос пользователя (первый prompt сессии)" >&2
cat >&2 <<EOF

Действие: построй таблицу + вердикт ✅/⚠️/❌ + что осталось.
Затем обнови recap.status = CLOSED или goal Phase 5.

Правило: ~/.claude/projects/-Users-antonk/memory/feedback_compare_goal_vs_result_session_end.md
Bypass: COMPARE_SKIP=1
EOF

exit 0
