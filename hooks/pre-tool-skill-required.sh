#!/usr/bin/env bash
# pre-tool-skill-required.sh — PreToolUse hook
#
# Блокирует Edit/Write/Bash если в последнем user-prompt есть keyword
# матчящий skill из ~/.claude/skills/, и этот skill не был вызван
# через Skill tool в текущей сессии.
#
# Bypass:
#   SKILL_OVERRIDE=1 ./pre-tool-skill-required.sh   # с явным обоснованием в env SKILL_REASON
#
# Whitelist tools (skip check): Read, Grep, Glob, Skill, TaskCreate, TaskUpdate,
#   TaskList, ToolSearch, AskUserQuestion, ScheduleWakeup, Bash (read-only)
#
# Self-disable triggers:
#   - в transcript уже есть Skill вызов с матчящим именем
#   - file /tmp/skill-required-done-{session_id} существует (manual snooze)

set -uo pipefail

# Bypass
if [[ "${SKILL_OVERRIDE:-0}" == "1" ]]; then
  echo "[skill-required] BYPASS via SKILL_OVERRIDE=1 (reason: ${SKILL_REASON:-unspecified})" >&2
  exit 0
fi

# Read tool input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

# Whitelist (read-only or already meta)
case "$TOOL_NAME" in
  Read|Grep|Glob|Skill|TaskCreate|TaskUpdate|TaskList|ToolSearch|AskUserQuestion|ScheduleWakeup) exit 0;;
  Write|Edit|Bash) :;;
  *) exit 0;;
esac

# Bash subset whitelist — git/touch/scp/curl/etc — read-only or sync ops
if [[ "$TOOL_NAME" == "Bash" ]]; then
  CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null | head -c 500)
  case "$CMD" in
    git\ *|*"&& git "*|*"; git "*) exit 0;;
    touch\ *|mkdir\ *|chmod\ *|chown\ *|ln\ *|cp\ *|mv\ *) exit 0;;
    ls\ *|cat\ *|head\ *|tail\ *|grep\ *|find\ *|wc\ *|file\ *) exit 0;;
    scp\ *|ssh\ *|rsync\ *|curl\ *|wget\ *) exit 0;;
    python3\ *|node\ *|npm\ *|pip\ *|brew\ *|crontab\ *) exit 0;;
    echo\ *|printf\ *|date|pwd|env|export\ *) exit 0;;
  esac
fi

[[ -z "$SESSION_ID" ]] && exit 0

# Snooze
if [[ -f "/tmp/skill-required-done-${SESSION_ID}" ]]; then
  exit 0
fi

TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
[[ ! -f "$TRANSCRIPT" ]] && exit 0

# Скиллы с триггерами в frontmatter — построим индекс skill_name → triggers (русск+англ)
SKILLS_DIR="$HOME/.claude/skills"
[[ ! -d "$SKILLS_DIR" ]] && exit 0

# Last user prompt (последняя user-message без role=tool_result)
LAST_USER=$(jq -r 'select(.message.role=="user") | .message.content | if type=="array" then (map(select(.type=="text") | .text) | join("\n")) else . end' "$TRANSCRIPT" 2>/dev/null \
  | tail -200 | tr 'А-Я' 'а-я' | tr 'A-Z' 'a-z')
[[ -z "$LAST_USER" ]] && exit 0

# Already-called skills в текущей сессии
CALLED_SKILLS=$(jq -r '.message.content[]? | select(.type=="tool_use" and .name=="Skill") | .input.skill // empty' "$TRANSCRIPT" 2>/dev/null | sort -u)

# Loop по доступным скиллам, ищем match по name+description в last_user
# Match только если skill-name появляется как ОТДЕЛЬНОЕ слово или /skill-name (slash-команда),
# а не как substring внутри другого слова (cro в "across", cons в "consilium" и т.п.).
# Минимальная длина skill-name для триггера — 5 символов (избегаем cro/api/seo как ложные).
MATCHED=""
for skill_md in "$SKILLS_DIR"/*/SKILL.md; do
  [[ ! -f "$skill_md" ]] && continue
  SKILL_NAME=$(basename "$(dirname "$skill_md")")
  # Skip archived
  [[ "$SKILL_NAME" == .* ]] && continue
  # Skip коротких имён — слишком много false-positive substring-матчей
  [[ ${#SKILL_NAME} -lt 5 ]] && continue

  # Skip already called
  echo "$CALLED_SKILLS" | grep -qx "$SKILL_NAME" && continue

  # Match только как /skill-name (явный вызов) ИЛИ word-boundary (отдельное слово)
  # grep -E '\b' не работает с дефисами надёжно — используем явные границы
  if echo "$LAST_USER" | grep -qE "(^|[[:space:]/])${SKILL_NAME}([[:space:]:,;.!?'\"]|\$)"; then
    MATCHED="$MATCHED $SKILL_NAME"
    break
  fi
done

if [[ -z "$MATCHED" ]]; then
  exit 0
fi

# BLOCK
SKILLS_LIST=$(echo "$MATCHED" | xargs -n1 | head -3 | sed 's/^/  • /')
cat >&2 <<EOF
[skill-required] ⛔ BLOCKED — пользователь упомянул skill, который не вызван:

${SKILLS_LIST}

Действие:
  1. Вызови Skill tool с этим именем (см. spec в ~/.claude/skills/<name>/SKILL.md)
  2. ИЛИ установи SKILL_OVERRIDE=1 + SKILL_REASON="why" если skill реально не подходит
  3. ИЛИ touch /tmp/skill-required-done-${SESSION_ID} чтобы заглушить (если ложное срабатывание)

Это правило защищает от паттерна «создал TaskCreate вместо вызова Skill».
EOF
exit 2
