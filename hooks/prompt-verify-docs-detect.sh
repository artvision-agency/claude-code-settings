#!/usr/bin/env bash
# prompt-verify-docs-detect.sh — UserPromptSubmit hook
#
# Детект технических "как X в Y / best practice / что лучше" запросов про
# конкретные библиотеки/API/framework. При совпадении — инжектит подсказку
# "[VERIFY-DOCS REQUIRED]" чтобы Claude вызвал /verify-from-docs или
# Context7 ДО написания кода (вместо ответа из pretraining).
#
# Не блокирует, только подсказывает (как prompt-skill-discovery.sh).
#
# Bypass: VERIFY_DOCS_OFF=1
# Snooze per-session: touch /tmp/verify-docs-done-{session_id}
#
# Self-disable условия:
#   - skill уже вызван в transcript
#   - или snooze-файл существует

set -uo pipefail
[[ "${VERIFY_DOCS_OFF:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[[ -z "$PROMPT" || -z "$SESSION_ID" ]] && exit 0
[[ -f "/tmp/verify-docs-done-${SESSION_ID}" ]] && exit 0
[[ ${#PROMPT} -lt 20 ]] && exit 0

# Lowercase + транслит русских "Е" в маленькие — для grep -i не хватает на ru
PROMPT_LC=$(echo "$PROMPT" | tr 'А-ЯA-Z' 'а-яa-z')

# === STEP 1: trigger pattern (ru + en) ===
# Любой из этих паттернов в prompt → potential candidate
TRIGGER=0
TRIGGER_REASON=""

if echo "$PROMPT_LC" | grep -qE '(как|how to)\s+(настроить|использовать|подключить|реализовать|вызвать|сделать|интегрировать|написать|configure|use|setup|integrate|call|implement)'; then
  TRIGGER=1
  TRIGGER_REASON="how-to"
fi

if echo "$PROMPT_LC" | grep -qE '(best practice|лучш(ая|ие) практик|что лучше|what.?s better|правильно ли|идиоматич)'; then
  TRIGGER=1
  TRIGGER_REASON="best-practice"
fi

if echo "$PROMPT_LC" | grep -qE '(official doc|документац|api reference|api docs|api спек)'; then
  TRIGGER=1
  TRIGGER_REASON="docs-ref"
fi

if echo "$PROMPT_LC" | grep -qE 'как работа(ет|ют)\s+\w'; then
  TRIGGER=1
  TRIGGER_REASON="how-works"
fi

[[ $TRIGGER -eq 0 ]] && exit 0

# === STEP 2: должна быть конкретная библиотека/API/framework в prompt'е ===
# Иначе вопрос абстрактный ("как настроить мониторинг" — общий, не нужен Context7)
LIBS_PATTERN='(react|next\.?js|vue|svelte|angular|fastapi|django|flask|express|nest|aiogram|grammy|telegraf|pydantic|sqlalchemy|drizzle|prisma|tailwind|shadcn|stripe|anthropic|openai|claude\s+(api|code|sdk)|playwright|puppeteer|telegram bot|telethon|node|deno|bun|webpack|vite|turbopack|eslint|prettier|jest|vitest|pytest|docker|kubernetes|nginx|postgres|mysql|redis|mongo|elastic|kafka|rabbitmq|graphql|grpc|websocket|oauth|jwt|cors|cdn|s3|cloudflare|vercel|netlify|aws|gcp|azure|terraform|ansible|gitlab|github actions|ci/?cd|webhook|cron|launchd|systemd|bash|zsh|powershell|python|typescript|javascript|rust|go(lang)?|java|kotlin|swift|sqlite|tg bot|api telegram|wordpress|modx|bitrix|tilda|notion|airtable|asana|slack|discord|figma|context7|mcp\s+server|aiohttp|httpx|requests|axios|fetch api|fastapi|gunicorn|uvicorn|celery|temporal|kafka|airflow|dbt|spark|pandas|numpy|scikit|pytorch|tensorflow|huggingface|langchain|llamaindex)'

if echo "$PROMPT_LC" | grep -qE "$LIBS_PATTERN"; then
  HAS_LIB=1
else
  HAS_LIB=0
fi

[[ $HAS_LIB -eq 0 ]] && exit 0

# === STEP 3: skill уже вызван в transcript? ===
TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
if [[ -f "$TRANSCRIPT" ]]; then
  if jq -r '.message.content[]? | select(.type=="tool_use" and .name=="Skill") | .input.skill // empty' "$TRANSCRIPT" 2>/dev/null \
     | grep -qxE 'verify-from-docs|docs-lookup'; then
    exit 0  # Уже вызван — не дёргаем
  fi
  # Context7 MCP уже вызван?
  if jq -r '.message.content[]? | select(.type=="tool_use") | .name // empty' "$TRANSCRIPT" 2>/dev/null \
     | grep -qE 'mcp__context7__'; then
    exit 0
  fi
fi

# === STEP 4: инжект подсказки ===
cat <<EOF
[VERIFY-DOCS] Запрос ($TRIGGER_REASON) про конкретную библиотеку/API.

ДО написания кода — проверь канонические доки, не отвечай из pretraining:
  1. \`mcp__context7__resolve-library-id\` → \`mcp__context7__query-docs\`
  2. ИЛИ Skill \`verify-from-docs\` (полный pipeline: Context7 + cookbook + github + round_table)
  3. ИЛИ Skill \`docs-lookup\` (упрощённая версия — только Context7)

Pretraining отстаёт на месяцы. API меняется. 2-3 минуты на проверку дешевле чем bug в проде.

Snooze: \`touch /tmp/verify-docs-done-${SESSION_ID}\`. Bypass для всей сессии: \`VERIFY_DOCS_OFF=1\`.
EOF

exit 0
