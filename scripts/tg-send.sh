#!/bin/bash
# tg-send.sh — thin wrapper over notify-telegram.sh с поддержкой каналов
# Usage: tg-send.sh <channel> "message"
#   channel: team (group chat), anton (DM)
set -euo pipefail

CHANNEL="${1:-team}"
shift || true
MSG="${*:-}"

if [ -z "$MSG" ]; then
    echo "Usage: tg-send.sh <team|anton> \"message\"" >&2
    exit 1
fi

case "$CHANNEL" in
    team)   export TELEGRAM_TEAM_CHAT_ID="-4273200821" ;;
    anton)  export TELEGRAM_TEAM_CHAT_ID="${TELEGRAM_ANTON_CHAT_ID:-326925698}" ;;
    *)      export TELEGRAM_TEAM_CHAT_ID="$CHANNEL" ;;  # custom chat_id
esac

exec "$(dirname "$0")/notify-telegram.sh" "$MSG"
