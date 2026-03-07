#!/bin/bash
# Stop hook: записать стоимость сессии в account-usage tracker
# и проверить — не пора ли переключить аккаунт
set -euo pipefail

TRACKER="$HOME/.claude/scripts/account-usage-tracker.sh"
[ -x "$TRACKER" ] || exit 0

# Получить текущий аккаунт
ACCOUNT=$(claude auth status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('email','unknown'))" 2>/dev/null || echo "unknown")
[ "$ACCOUNT" = "unknown" ] && exit 0

# Получить стоимость из stdin (Stop hook получает session data)
# Fallback: если стоимость не передана, пропускаем
COST="${CLAUDE_SESSION_COST:-0}"

# Записать
"$TRACKER" log "$ACCOUNT" "$COST" > /dev/null 2>&1 || true

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

    # TG alert
    TOKEN_FILE="$HOME/artvision-data/tokens.json"
    if [ -f "$TOKEN_FILE" ]; then
        TG_TOKEN=$(python3 -c "import json; d=json.load(open('$TOKEN_FILE')); print(d['telegram']['portal_bot']['token'])" 2>/dev/null || true)
        CHAT_ID=$(python3 -c "import json; d=json.load(open('$TOKEN_FILE')); print(d['telegram']['group_chat_id'])" 2>/dev/null || true)
        if [ -n "$TG_TOKEN" ] && [ -n "$CHAT_ID" ]; then
            MSG="Claude Max: $CURRENT at ${CUR_PCT}% weekly limit. Switch to $OTHER (${OTHER_PCT}%)."
            curl -s "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
                -d "chat_id=${CHAT_ID}" \
                -d "text=${MSG}" > /dev/null 2>&1 || true
        fi
    fi
fi
