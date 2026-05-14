#!/usr/bin/env bash
# Hero label КП клиента не должен дублировать hero других КП в presales/
set -uo pipefail
[[ "${HERO_UNIQUE_OK:-0}" == "1" ]] && exit 0
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ ! "$TOOL" =~ ^(Write|Edit)$ ]] && exit 0
[[ ! "$FILE" =~ presales/.+/kp/.+\.html$ ]] && exit 0
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)
[[ -z "$CONTENT" ]] && exit 0
HERO=$(echo "$CONTENT" | grep -oE '<div class="hero-label">[^<]+</div>' | head -1)
[[ -z "$HERO" ]] && exit 0
# Поиск этой же hero в других КП
CUR_SLUG=$(echo "$FILE" | sed -E 's|.*presales/([^/]+)/kp/.*|\1|')
DUPS=$(grep -rl "$HERO" /Users/antonk/artvision-data/presales/*/kp/*.html 2>/dev/null | grep -v "/$CUR_SLUG/" | head -2)
if [[ -n "$DUPS" ]]; then
    echo "⚠️  WARN: pre-kp-hero-unique: тот же hero у других КП:" >&2
    echo "$DUPS" | sed 's|^|  • |' >&2
    echo "Поправь hero под этого клиента (домен, ниша, тон). Bypass: HERO_UNIQUE_OK=1" >&2
    exit 0  # warning-only mode (was blocking)
fi
exit 0
