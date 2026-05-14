#!/usr/bin/env bash
# Размер рынка / доля рынка в КП — обязателен дисклеймер «не TAM/SAM»
set -uo pipefail
[[ "${MARKET_DISCLAIMER_OK:-0}" == "1" ]] && exit 0
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ ! "$TOOL" =~ ^(Write|Edit)$ ]] && exit 0
[[ ! "$FILE" =~ presales/.+/kp/.+\.html$ ]] && exit 0
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)
[[ -z "$CONTENT" ]] && exit 0
# Если упоминается «размер рынка» / «доля рынка» — должен быть дисклеймер
if echo "$CONTENT" | grep -qiE 'размер рынка|доля рынка|рыночн.{0,10}объ[её]м'; then
    if ! echo "$CONTENT" | grep -qiE 'не TAM|не SAM|выборк.{0,30}ключ|это не весь рынок|реальный рынок.{0,30}шире'; then
        echo "⚠️  WARN:  WARN: pre-kp-market-disclaimer: «размер/доля рынка» без дисклеймера. Это выборка N ключей, не TAM/SAM. Bypass: MARKET_DISCLAIMER_OK=1" >&2
        exit 0  # warning-only mode (was blocking)
    fi
fi
exit 0
