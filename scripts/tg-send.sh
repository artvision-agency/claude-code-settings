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
    ppc)    CHAT_ID="-4564169720" ;;  # AV: Контекстная, Аналитика, PPC (Антон/Андрей/Дима)
    *)      CHAT_ID="$CHANNEL" ;;
esac
export TELEGRAM_TEAM_CHAT_ID="$CHAT_ID"

# Отправка + capture output (msg_id), с ретраем на ТРАНЗИЕНТНЫЕ сетевые сбои.
# Прецедент 29.05.2026: daily-summary BluMart упал curl_rc=35 (SSL_ERROR_SYSCALL),
# алёрт молча суппрессировался. Ретраим только сеть (SSL/connect/timeout/DNS),
# НЕ API-отказы (403/400 — там ретрай бесполезен).
RESPONSE=""
SENT=0
for attempt in 1 2 3; do
    if RESPONSE="$("$(dirname "$0")/notify-telegram.sh" "$MSG" 2>&1)"; then
        SENT=1
        break
    fi
    if [ "$attempt" -lt 3 ] && printf '%s' "$RESPONSE" \
        | grep -qE 'curl_rc=(6|7|28|35|56)\b|SSL_ERROR|Network error|Could not resolve|Connection timed out|Operation timed out'; then
        sleep "$((attempt * 3))"
        continue
    fi
    break
done

if [ "$SENT" -ne 1 ]; then
    echo "$RESPONSE" >&2
    # Лог провала тоже пишем
    HANDOFF="$HOME/artvision-data/sync/HANDOFF_$(date +%Y-%m-%d).md"
    mkdir -p "$(dirname "$HANDOFF")"
    [ -f "$HANDOFF" ] || printf "# Handoff %s\n\n## TG Sends Log\n\n" "$(date +%Y-%m-%d)" > "$HANDOFF"
    printf -- "- %s | channel=%s | chat_id=%s | ❌ FAIL (after retry) | msg=%q\n" "$(date -u +%H:%M:%SZ)" "$CHANNEL" "$CHAT_ID" "${MSG:0:120}" >> "$HANDOFF"
    exit 1
fi

echo "$RESPONSE"

# Append to HANDOFF journal
HANDOFF="$HOME/artvision-data/sync/HANDOFF_$(date +%Y-%m-%d).md"
mkdir -p "$(dirname "$HANDOFF")"
[ -f "$HANDOFF" ] || printf "# Handoff %s\n\n## TG Sends Log\n\n" "$(date +%Y-%m-%d)" > "$HANDOFF"
# `|| true`: при ответе "✅ Sent" (не JSON) grep не находит message_id → под
# set -e + pipefail pipeline=1 убивал скрипт ПОСЛЕ успешной отправки → daily-summary
# логировал «send failed rc=1» при доставленном сообщении. Прецедент 29.05.2026.
MSG_ID="$(printf '%s' "$RESPONSE" | grep -oE '"message_id":[0-9]+' | head -1 | cut -d: -f2 || true)"
printf -- "- %s | channel=%s | chat_id=%s | msg_id=%s | msg=%q\n" \
    "$(date -u +%H:%M:%SZ)" "$CHANNEL" "$CHAT_ID" "${MSG_ID:-?}" "${MSG:0:120}" >> "$HANDOFF"
