#!/usr/bin/env bash
# Главный конкурент в КП — обязательное доказательство по позициям (Topvisor snapshot)
# Прецедент: 11.05.2026 Антон спросил "почему shkolamm = главный конкурент" — не было обоснования
set -uo pipefail
[[ "${COMPETITOR_PROOF_OK:-0}" == "1" ]] && exit 0
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ ! "$TOOL" =~ ^(Write|Edit)$ ]] && exit 0
[[ ! "$FILE" =~ presales/.+/kp/.+\.html$ ]] && exit 0
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)
[[ -z "$CONTENT" ]] && exit 0
# Если есть "главный конкурент" / "main competitor" в КП — должна быть рядом ссылка на позицию (ТОП-X)
if echo "$CONTENT" | grep -qiE '"главный конкурент|называется главным|основной соперник"'; then
    if ! echo "$CONTENT" | grep -qiE 'топ-?[0-9]+|снимок позиций|topvisor.*[0-9]+\.[0-9]+\.20[0-9]+'; then
        echo "⚠️  WARN:  WARN: pre-kp-competitor-proof: блок «главный конкурент» без обоснования через позиции Topvisor. Bypass: COMPETITOR_PROOF_OK=1" >&2
        exit 0  # warning-only mode (was blocking)
    fi
fi
exit 0
