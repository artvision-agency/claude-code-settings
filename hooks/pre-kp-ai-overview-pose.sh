#!/usr/bin/env bash
# Колонка «AI блок» / «Генератив. ответ» — пометка «оценка» если нет ai-overview-detection.json
set -uo pipefail
[[ "${AI_POSE_OK:-0}" == "1" ]] && exit 0
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ ! "$TOOL" =~ ^(Write|Edit)$ ]] && exit 0
[[ ! "$FILE" =~ presales/.+/kp/.+\.html$ ]] && exit 0
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)
[[ -z "$CONTENT" ]] && exit 0
# Если есть колонка «AI блок» или «Генератив. ответ» — должна быть пометка «оценка» или ссылка на ai-overview JSON
if echo "$CONTENT" | grep -qiE 'AI[- ]блок|Генератив.{0,5}ответ|нейроассистент.*вы?дача'; then
    SLUG=$(echo "$FILE" | sed -E 's|.*presales/([^/]+)/kp/.*|\1|')
    AI_JSON="/Users/antonk/artvision-data/clients/${SLUG}/seo/$(date +%Y-%m-%d)/ai-overview-detection.json"
    if [[ ! -f "$AI_JSON" ]] && ! echo "$CONTENT" | grep -qiE 'оценка|эвристик|heuristic'; then
        echo "⚠️  WARN:  WARN: pre-kp-ai-overview-pose: колонка про AI/нейровыдачу без пометки «оценка» или JSON-snapshot. Bypass: AI_POSE_OK=1" >&2
        exit 0  # warning-only mode (was blocking)
    fi
fi
exit 0
