#!/usr/bin/env bash
# UserPromptSubmit hook: если промпт содержит план из ≥3 шагов (numbered/bullet),
# предлагает использовать superpowers:subagent-driven-development.
# Self-disables after first nudge (per session via /tmp flag).
# Also skips if skill already called in transcript.
#
# Bypass: SUBAGENT_SUGGEST_FORCE=0  — пропуск без подсказки (для тестов)
# Disable per-session: touch /tmp/subagent-driven-nudged-${SESSION_ID}

set -uo pipefail

[[ "${SUBAGENT_SUGGEST_FORCE:-1}" == "0" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)

# Без session_id или prompt — молчим
[[ -z "$SESSION_ID" || -z "$PROMPT" ]] && exit 0

# Self-disable: уже нудали в этой сессии
[[ -f "/tmp/subagent-driven-nudged-${SESSION_ID}" ]] && exit 0

# Self-disable: skill уже вызывался в транскрипте
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
  if grep -q '"skill":"superpowers:subagent-driven-development"' "$TRANSCRIPT" 2>/dev/null; then
    exit 0
  fi
fi

# Эвристика «длинный план»: считаем строки-шаги (numbered или bullet)
STEP_COUNT=$(printf '%s' "$PROMPT" | grep -cE '^\s*[0-9]+[.))]|^\s*[-*] ' 2>/dev/null || true)
STEP_COUNT="${STEP_COUNT//[$'\t\r\n ']/}"
STEP_COUNT="${STEP_COUNT:-0}"
[[ "$STEP_COUNT" -lt 3 ]] && exit 0

# Нудим один раз
touch "/tmp/subagent-driven-nudged-${SESSION_ID}"

cat << EOF
[SUGGESTED-SKILL] У этой задачи ≥${STEP_COUNT} шагов. Рекомендую superpowers:subagent-driven-development — subagent работает автономно 2+ часа без отклонений.
Альтернатива: продолжай как обычно, hook молчит до конца сессии.
EOF

exit 0
