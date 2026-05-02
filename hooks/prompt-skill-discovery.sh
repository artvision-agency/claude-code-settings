#!/usr/bin/env bash
# prompt-skill-discovery.sh — UserPromptSubmit hook
#
# При новом user prompt находит релевантные skills (по описанию)
# и инжектит подсказку «Под эту задачу могут подойти: X / Y / Z».
#
# Bypass: SKILL_DISCOVERY_OFF=1
# Suppress per-session: touch /tmp/skill-discovery-done-{session_id}

set -uo pipefail
[[ "${SKILL_DISCOVERY_OFF:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[[ -z "$PROMPT" || -z "$SESSION_ID" ]] && exit 0
[[ -f "/tmp/skill-discovery-done-${SESSION_ID}" ]] && exit 0

# Skip короткие prompts (меньше 30 символов)
[[ ${#PROMPT} -lt 30 ]] && exit 0

SKILLS_DIR="$HOME/.claude/skills"
[[ ! -d "$SKILLS_DIR" ]] && exit 0

PROMPT_LOWER=$(echo "$PROMPT" | tr 'А-Я' 'а-я' | tr 'A-Z' 'a-z')

# Простой scoring — match keywords из description
declare -A SCORES
for skill_md in "$SKILLS_DIR"/*/SKILL.md; do
  [[ ! -f "$skill_md" ]] && continue
  SKILL_NAME=$(basename "$(dirname "$skill_md")")
  [[ "$SKILL_NAME" == .* ]] && continue

  DESC=$(awk '/^description:/{flag=1; sub(/^description:[[:space:]]*/,""); print; next} /^---/{flag=0} flag' "$skill_md" \
    | head -5 | tr 'А-Я' 'а-я' | tr 'A-Z' 'a-z' | tr '\n' ' ')

  # Берём 5 первых "длинных" слов (>4 символов) из description
  KEYWORDS=$(echo "$DESC" | grep -oE '[a-zа-я][a-zа-я-]{4,}' | head -10)

  SCORE=0
  while IFS= read -r kw; do
    [[ -z "$kw" ]] && continue
    if echo "$PROMPT_LOWER" | grep -q -- "$kw"; then
      SCORE=$((SCORE + 1))
    fi
  done <<< "$KEYWORDS"

  # Bonus за упоминание имени скилла
  if echo "$PROMPT_LOWER" | grep -q -- "$SKILL_NAME"; then
    SCORE=$((SCORE + 5))
  fi

  if [[ $SCORE -ge 3 ]]; then
    SCORES[$SKILL_NAME]=$SCORE
  fi
done

# Top-5
[[ ${#SCORES[@]} -eq 0 ]] && exit 0

TOP=$(for k in "${!SCORES[@]}"; do echo "${SCORES[$k]} $k"; done | sort -rn | head -5)

cat <<EOF
[SKILL-DISCOVERY] Под эту задачу могут подойти скиллы (по описанию):

$(echo "$TOP" | awk '{printf "  • %s (score=%s)\n", $2, $1}')

Если задача попадает в их домен — ВЫЗОВИ Skill tool с этим именем,
а не имитируй через Bash/Agent. После использования: touch /tmp/skill-discovery-done-${SESSION_ID}
если хочешь заглушить на сессию.
EOF
exit 0
