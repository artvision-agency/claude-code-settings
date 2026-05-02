#!/bin/bash
# tg-send.sh — thin wrapper over notify-telegram.sh с поддержкой каналов + автолог в HANDOFF
# Usage: tg-send.sh <channel> "message"
#   channel: team (group chat), anton (DM), <chat_id> (custom)
set -euo pipefail

CHANNEL="${1:-team}"
shift || true
MSG="${*:-}"

if [ -z "$MSG" ]; then
    echo "Usage: tg-send.sh <team|anton|chat_id> \"message\"" >&2
    exit 1
fi

case "$CHANNEL" in
    team)   CHAT_ID="-4273200821" ;;
    anton)  CHAT_ID="${TELEGRAM_ANTON_CHAT_ID:-161261562}" ;;
    *)      CHAT_ID="$CHANNEL" ;;
esac
export TELEGRAM_TEAM_CHAT_ID="$CHAT_ID"

# Отправка + capture output (msg_id)
RESPONSE="$("$(dirname "$0")/notify-telegram.sh" "$MSG" 2>&1)" || {
    echo "$RESPONSE" >&2
    # Лог провала тоже пишем
    HANDOFF="$HOME/artvision-data/sync/HANDOFF_$(date +%Y-%m-%d).md"
    mkdir -p "$(dirname "$HANDOFF")"
    [ -f "$HANDOFF" ] || printf "# Handoff %s\n\n## TG Sends Log\n\n" "$(date +%Y-%m-%d)" > "$HANDOFF"
    printf -- "- %s | channel=%s | chat_id=%s | ❌ FAIL | msg=%q\n" "$(date -u +%H:%M:%SZ)" "$CHANNEL" "$CHAT_ID" "${MSG:0:120}" >> "$HANDOFF"
    exit 1
}

echo "$RESPONSE"

# Append to HANDOFF journal
HANDOFF="$HOME/artvision-data/sync/HANDOFF_$(date +%Y-%m-%d).md"
mkdir -p "$(dirname "$HANDOFF")"
[ -f "$HANDOFF" ] || printf "# Handoff %s\n\n## TG Sends Log\n\n" "$(date +%Y-%m-%d)" > "$HANDOFF"
MSG_ID="$(printf '%s' "$RESPONSE" | grep -oE '"message_id":[0-9]+' | head -1 | cut -d: -f2)"
printf -- "- %s | channel=%s | chat_id=%s | msg_id=%s | msg=%q\n" \
    "$(date -u +%H:%M:%SZ)" "$CHANNEL" "$CHAT_ID" "${MSG_ID:-?}" "${MSG:0:120}" >> "$HANDOFF"
