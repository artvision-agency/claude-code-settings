#!/usr/bin/env bash
# prompt-medical-mcp-reminder.sh — UserPromptSubmit хук.
#
# Если в промпте есть медицинские keyword'ы → инжектит напоминание включить
# медицинские MCP-серверы (если они отключены): healthcare-mcp, medical-mcp.
# PubMed (claude_ai_PubMed) обычно держим включённым.
#
# Self-disable после одного срабатывания в сессии (флаг /tmp/medical-mcp-reminded.<sid>).

set -uo pipefail

input="$(cat || true)"
session_id=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
prompt=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null || echo "")

[ -z "$prompt" ] && exit 0

# Self-disable per session
flag="/tmp/medical-mcp-reminded.${session_id:-default}"
[ -f "$flag" ] && exit 0

# Медицинские keyword'ы (рус + англ)
KW='медицин|врач|клиник|пациент|болезн|лечен|стоматолог|онколог|кардио|неврол|психиатр|терапевт|диагноз|симптом|препарат|лекарств|вакцин|клинические испытан|медкарт|анализы|МРТ|КТ|УЗИ|pubmed|FDA|ICD|drug interaction|clinical trial|symptoms|diagnosis|treatment protocol|medical literature|patient case'

if ! echo "$prompt" | grep -qiE "$KW"; then
  exit 0
fi

# Создаём флаг чтобы не дублировать
touch "$flag"

# Инжектим напоминание
python3 - <<'PY'
import json
msg = """💊 Медицинский контекст в запросе.

Если ответ требует доступа к научной литературе/препаратам/гайдлайнам — включи в claude.ai → Settings → Connectors:
  • PubMed              (научные публикации)
  • healthcare-mcp      (FDA drug lookup, клинические испытания, ICD коды, BMI и др.)
  • medical-mcp         (Google Scholar, AAP guidelines, педиатрия)

После включения Reconnect = кнопка в UI, токены сохранены.
Это напоминание один раз за сессию."""
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg
    }
}))
PY
