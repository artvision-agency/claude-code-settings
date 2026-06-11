#!/usr/bin/env bash
# prompt-parallel-skills-detect.sh — UserPromptSubmit hook
#
# Детектит класс задачи из 4 групп (SEO/factcheck/code-review/research) и
# инжектит system-reminder: «запусти 2-3 скилла параллельно + консолидируй».
#
# Bypass: PARALLEL_SKILLS_OFF=1
# Suppress per-session: touch /tmp/parallel-skills-done-{session_id}
# Skip current prompt: prompt содержит «только», «just», «not parallel», «no parallel»
#
# Rule: ~/.claude/rules/parallel-skill-groups.md
# Registry: ~/.claude/scripts/parallel-skills-registry.json

set -uo pipefail
[[ "${PARALLEL_SKILLS_OFF:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)

[[ -z "$PROMPT" || -z "$SESSION_ID" ]] && exit 0

# Один раз за сессию — потом тихо (анти-спам)
FLAG="/tmp/parallel-skills-done-${SESSION_ID}"
[[ -f "$FLAG" ]] && exit 0

# Минимум 20 символов чтобы не реагировать на «го», «1», «туду»
[[ ${#PROMPT} -lt 20 ]] && exit 0

PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Skip-conditions — пользователь явно отказывается от параллели
if echo "$PROMPT_LOWER" | grep -qE "(только один|just one|no parallel|not parallel|без параллел|один скилл|single skill)"; then
  exit 0
fi

REGISTRY="$HOME/.claude/scripts/parallel-skills-registry.json"
[[ ! -f "$REGISTRY" ]] && exit 0

# Детект класса: пройти по группам, найти совпадение триггера
MATCHED_GROUP=""
MATCHED_TRIGGERS=""

while IFS= read -r group_id; do
  while IFS= read -r trigger; do
    [[ -z "$trigger" ]] && continue
    if echo "$PROMPT_LOWER" | grep -qF "$trigger"; then
      MATCHED_GROUP="$group_id"
      MATCHED_TRIGGERS="$trigger"
      break 2
    fi
  done < <(jq -r --arg gid "$group_id" '.groups[] | select(.id==$gid) | .triggers[]?' "$REGISTRY" 2>/dev/null)
done < <(jq -r '.groups[].id' "$REGISTRY" 2>/dev/null)

[[ -z "$MATCHED_GROUP" ]] && exit 0

# Получить дефолтные скиллы для группы
case "$MATCHED_GROUP" in
  "research-market")
    # research имеет 2 варианта
    if echo "$PROMPT_LOWER" | grep -qE "(конкурент|competitor)"; then
      SKILLS=$(jq -r '.groups[] | select(.id=="research-market") | .default_skills_competitor | join(" + ")' "$REGISTRY")
    else
      SKILLS=$(jq -r '.groups[] | select(.id=="research-market") | .default_skills_market | join(" + ")' "$REGISTRY")
    fi
    ;;
  "factcheck-kp")
    # finance vs обычный
    MONEY_KW=$(jq -r '.groups[] | select(.id=="factcheck-kp") | .money_document_keywords[]?' "$REGISTRY" 2>/dev/null)
    IS_MONEY=0
    for kw in $MONEY_KW; do
      if echo "$PROMPT_LOWER" | grep -qF "$kw"; then
        IS_MONEY=1
        break
      fi
    done
    if [[ "$IS_MONEY" == "1" ]]; then
      SKILLS="/factcheck + /finance-factcheck + strict-factchecker (agent)"
    else
      SKILLS=$(jq -r '.groups[] | select(.id=="factcheck-kp") | (.default_skills + (.default_agents | map(. + " (agent)"))) | join(" + ")' "$REGISTRY")
    fi
    ;;
  *)
    SKILLS=$(jq -r --arg gid "$MATCHED_GROUP" '.groups[] | select(.id==$gid) | .default_skills | join(" + ")' "$REGISTRY")
    ;;
esac

GROUP_NAME=$(jq -r --arg gid "$MATCHED_GROUP" '.groups[] | select(.id==$gid) | .name' "$REGISTRY")

# Установить флаг чтобы не повторять
touch "$FLAG"

# Логирование
LOG="$HOME/.claude/logs/parallel-skills-detect.log"
mkdir -p "$(dirname "$LOG")"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | session=$SESSION_ID | group=$MATCHED_GROUP | trigger='$MATCHED_TRIGGERS' | skills=$SKILLS" >> "$LOG"

# Инжект system-reminder (quoted heredoc — без подстановок, потом sed)
HEADER="[PARALLEL-SKILLS DETECTED]"
LINE1="Класс задачи: **${GROUP_NAME}** (триггер: «${MATCHED_TRIGGERS}»)"
LINE2="1. Запустить **параллельно** скиллы: ${SKILLS}"

printf '%s\n' "$HEADER"
printf '%s\n\n' "$LINE1"
cat << 'EOF'
Правило ~/.claude/rules/parallel-skill-groups.md требует:
EOF
printf '%s\n' "$LINE2"
cat << 'EOF'
2. После прогона — **консолидировать** результаты:
   - dedup по ключу группы (URL+issue / file:line / claim+source)
   - severity-rank: CRITICAL > HIGH > MID > LOW
   - cross-confirmation: 2+ скилла подтверждают = высокая уверенность
   - уникальные находки одного скилла оставить
3. В **первой строке** ответа показать: [PARALLEL: 3 skills — <list>, ~$1.20]
4. Финальный артефакт — единый отчёт с пометкой источников [skill-A+skill-B]

Пропустить параллель если:
- Это правка <5 мин (одна опечатка)
- Уже был параллельный прогон в этой сессии по этой же задаче
- Пользователь явно сказал «только X»

Bypass на одну сессию: PARALLEL_SKILLS_OFF=1
EOF

exit 0
