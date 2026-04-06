#!/bin/bash
# Stop hook: записать сессию в account-usage tracker
# Claude Max = подписка, считаем СЕССИИ (не доллары)
set -euo pipefail

TRACKER="$HOME/.claude/scripts/account-usage-tracker.sh"
[ -x "$TRACKER" ] || exit 0

# Получить текущий аккаунт
ACCOUNT=$(claude auth status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('email','unknown'))" 2>/dev/null || echo "unknown")
[ "$ACCOUNT" = "unknown" ] && exit 0

# Прочитать stdin — Claude Code может передать JSON с session data
STDIN_DATA=""
if [ ! -t 0 ]; then
    STDIN_DATA=$(cat 2>/dev/null || true)
fi

# Извлечь num_turns из stdin JSON (если есть)
NUM_TURNS=0
if [ -n "$STDIN_DATA" ]; then
    NUM_TURNS=$(echo "$STDIN_DATA" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Попробовать разные поля
    turns = data.get('num_turns', data.get('numTurns', data.get('turns', 0)))
    print(int(turns) if turns else 0)
except:
    print(0)
" 2>/dev/null || echo "0")
fi

# Fallback: считать 1 сессию даже без turns
[ "$NUM_TURNS" -eq 0 ] 2>/dev/null && NUM_TURNS=1

# ═══ Latency tracking ═══
LATENCY_LOG="$HOME/.claude/latency.csv"
if [ ! -f "$LATENCY_LOG" ]; then
    echo "date,account,turns,session_duration_min" > "$LATENCY_LOG"
fi
SESSION_START="${CLAUDE_SESSION_START:-}"
if [ -n "$SESSION_START" ]; then
    NOW=$(date +%s)
    DURATION_MIN=$(( (NOW - SESSION_START) / 60 ))
else
    DURATION_MIN=0
fi
echo "$(date +%Y-%m-%d_%H:%M),$ACCOUNT,$NUM_TURNS,$DURATION_MIN" >> "$LATENCY_LOG" 2>/dev/null || true

# Записать сессию
"$TRACKER" log "$ACCOUNT" "$NUM_TURNS" > /dev/null 2>&1 || true

# Проверить лимит
RESULT=$("$TRACKER" check 2>/dev/null || echo "OK|unknown|0")
STATUS=$(echo "$RESULT" | cut -d'|' -f1)

if [ "$STATUS" = "SWITCH_NEEDED" ]; then
    CURRENT=$(echo "$RESULT" | cut -d'|' -f2)
    OTHER=$(echo "$RESULT" | cut -d'|' -f3)
    CUR_PCT=$(echo "$RESULT" | cut -d'|' -f4)
    OTHER_PCT=$(echo "$RESULT" | cut -d'|' -f5)

    echo "ACCOUNT LIMIT WARNING: $CURRENT at ${CUR_PCT}% of weekly limit!"
    echo "Switch to $OTHER (${OTHER_PCT}% used):"
    echo "  claude auth logout && claude auth login --email $OTHER"

    # TG alert (дедупликация: макс 1 раз в час)
    ALERT_FLAG="$HOME/.claude/.account-alert-sent"
    SEND_ALERT=true
    if [ -f "$ALERT_FLAG" ]; then
        LAST_ALERT=$(cat "$ALERT_FLAG" 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        DIFF=$(( NOW_EPOCH - LAST_ALERT ))
        [ "$DIFF" -lt 3600 ] && SEND_ALERT=false
    fi

    if [ "$SEND_ALERT" = "true" ]; then
        TOKEN_FILE="$HOME/artvision-data/tokens.json"
        if [ -f "$TOKEN_FILE" ]; then
            TG_TOKEN=$(python3 -c "import json; d=json.load(open('$TOKEN_FILE')); print(d['telegram']['portal_bot']['token'])" 2>/dev/null || true)
            CHAT_ID=$(python3 -c "import json; d=json.load(open('$TOKEN_FILE')); print(d['telegram']['group_chat_id'])" 2>/dev/null || true)
            if [ -n "$TG_TOKEN" ] && [ -n "$CHAT_ID" ]; then
                MSG="⚠️ Claude Max: $CURRENT — ${CUR_PCT}% лимита. Переключись на $OTHER (${OTHER_PCT}%)."
                curl -s "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
                    -d "chat_id=${CHAT_ID}" \
                    -d "text=${MSG}" > /dev/null 2>&1 || true
                date +%s > "$ALERT_FLAG"
            fi
        fi
    fi
fi
