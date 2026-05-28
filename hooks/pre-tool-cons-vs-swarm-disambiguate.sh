#!/bin/bash
# pre-tool-cons-vs-swarm-disambiguate.sh
# PreToolUse hook on Skill tool.
# Цель: ловить когда Антон явно сказал «рой/делать» а Claude вызывает /cons,
#       или сказал «консилиум/думать» а Claude вызывает /swarm.
#
# Семантика (см. memory/feedback_cons_vs_swarm_disambiguate.md):
#   - /cons  = ДУМАТЬ (анализ, решение, decision-making)
#   - /swarm = ДЕЛАТЬ (test+fix+verify, реализация)
#   - mixed промпт = /cons → /swarm пайплайн
#
# Bypass: CONS_SWARM_FORCE=1

[ "${CONS_SWARM_FORCE:-0}" = "1" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"

# Tool name + skill name extraction
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
[ "$TOOL" != "Skill" ] && exit 0

SKILL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('skill',''))" 2>/dev/null)
[ "$SKILL" != "cons" ] && [ "$SKILL" != "swarm" ] && exit 0

# Find last user prompt from transcript
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
[ -z "$SESSION_ID" ] && exit 0

TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/$SESSION_ID.jsonl"
[ ! -f "$TRANSCRIPT" ] && exit 0

# Get last user-role text (skip system-reminders)
LAST_USER=$(python3 <<PYEOF 2>/dev/null
import json
import sys
try:
    last = ""
    with open("$TRANSCRIPT") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get('type') != 'user':
                continue
            msg = obj.get('message', {})
            content = msg.get('content', '')
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict) and 'text' in c:
                        parts.append(c['text'])
                content = ' '.join(parts)
            if not content or not isinstance(content, str):
                continue
            if 'system-reminder' in content or 'SKILL-DISCOVERY' in content:
                continue
            last = content[:500].lower()
    print(last)
except Exception:
    pass
PYEOF
)

[ -z "$LAST_USER" ] && exit 0

# Mismatch detection
WARN=""
if [ "$SKILL" = "cons" ]; then
    if echo "$LAST_USER" | grep -qE 'рой|сделай|реализу|пофикси|deploy|залей|выполни'; then
        if ! echo "$LAST_USER" | grep -qE 'консилиум|стратсесси|обсуди|думай|рассужд|собери|cons|подумай'; then
            WARN="cons (думать) при ДЕЛАТЬ-триггере"
        fi
    fi
fi

if [ "$SKILL" = "swarm" ]; then
    if echo "$LAST_USER" | grep -qE 'консилиум|стратсесси|обсуди|думай|рассужд|разбери|оцени|анализ'; then
        if ! echo "$LAST_USER" | grep -qE 'рой|сделай|реализу|пофикси|swarm|делайте'; then
            WARN="swarm (делать) при ДУМАТЬ-триггере"
        fi
    fi
fi

[ -z "$WARN" ] && exit 0

cat <<EOF >&2
⚠️  cons-vs-swarm-disambiguate: возможный mismatch
   Skill: /$SKILL
   Mismatch: $WARN
   Last user prompt: $(echo "$LAST_USER" | head -c 120)

Семантика (feedback_cons_vs_swarm_disambiguate.md):
  /cons  = ДУМАТЬ (анализ, решение)
  /swarm = ДЕЛАТЬ (реализация, фикс)

Если Антон сказал «соберитесь + сделайте» — нужен пайплайн /cons → /swarm.
Если уверен в выборе — bypass: CONS_SWARM_FORCE=1
EOF

# Warn but don't block (exit 0) — let Claude proceed
exit 0
