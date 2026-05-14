#!/usr/bin/env bash
# В секции #backlinks обязателен CSS-bars chart (не только таблица)
set -uo pipefail
[[ "${BACKLINKS_VISUAL_OK:-0}" == "1" ]] && exit 0
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ "$TOOL" != "Write" ]] && exit 0
[[ ! "$FILE" =~ presales/.+/kp/.+\.html$ ]] && exit 0
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null)
[[ -z "$CONTENT" ]] && exit 0
# Если в КП есть #backlinks секция — должен быть rd-bars chart
if echo "$CONTENT" | grep -qE 'id="backlinks"'; then
    if ! echo "$CONTENT" | grep -qE 'class="rd-bars|class="backlinks-chart|<svg.*backlinks'; then
        echo "⚠️  WARN: pre-kp-backlinks-visual: #backlinks без визуального графика. Добавь CSS-bars chart по RD доменов. Bypass: BACKLINKS_VISUAL_OK=1" >&2
        exit 0  # warning-only mode (was blocking)
    fi
fi
exit 0
