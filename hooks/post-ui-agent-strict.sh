#!/usr/bin/env bash
# post-ui-agent-strict.sh
# Hook: PostToolUse on SubagentStop / Agent для UI-агентов
# Прецедент: 15.05.2026 ui-designer выдумал rating ~3.8 для школы «Шамир» (нет в JSON)
# Действие: warn user после завершения UI-агента → предложить запустить strict-факчек
# Bypass: UI_STRICT_OFF=1

set -euo pipefail

if [[ "${UI_STRICT_OFF:-}" = "1" ]]; then
    exit 0
fi

INPUT=$(cat)

# Hook fires on SubagentStop event. We want to act only when subagent was UI-related.
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .hook_event_name // empty' 2>/dev/null || echo "")

# Try to extract subagent_type from various positions
SUBAGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // .subagent_type // .agent_type // empty' 2>/dev/null || echo "")
DESCRIPTION=$(echo "$INPUT" | jq -r '.tool_input.description // .description // empty' 2>/dev/null || echo "")
PROMPT_PREVIEW=$(echo "$INPUT" | jq -r '.tool_input.prompt // .prompt // empty' 2>/dev/null | head -c 1500 || echo "")

# UI-agent triggers: subagent_type contains "ui" or "design" or "frontend"
IS_UI=0
LOWER="$(echo "$SUBAGENT_TYPE $DESCRIPTION" | tr '[:upper:]' '[:lower:]')"
if echo "$LOWER" | grep -qE "ui-designer|ui-ux|frontend-design|design-system|frontend-developer|landing-page"; then
    IS_UI=1
fi
# Also check if prompt mentions HTML generation with numbers
if [[ "$IS_UI" = "0" ]] && echo "$PROMPT_PREVIEW" | grep -qiE "html|css.*chart|heatmap|bar.*chart|tier.*card|dashboard"; then
    IS_UI=1
fi

if [[ "$IS_UI" = "0" ]]; then
    exit 0
fi

# Inject reminder via stderr (Claude sees in next turn)
{
    echo ""
    echo "📊 [post-ui-agent-strict] UI-агент завершил работу."
    echo ""
    echo "  Прецедент 15.05.2026: ui-designer добавил CSS-bars и подвыдумал rating ~3.8"
    echo "  для школы «Шамир», которого нет в JSON-источниках."
    echo ""
    echo "  Рекомендация: вызови strict-factchecker на изменённый HTML до deploy."
    echo ""
    echo "  Команда:"
    echo "    Agent(subagent_type=\"strict-factchecker\", prompt=\"Проверь свежие числа в HTML против JSON-источников...\")"
    echo ""
    echo "  Bypass: UI_STRICT_OFF=1"
    echo ""
} >&2

# Exit 0 — это soft reminder, не блок
exit 0
