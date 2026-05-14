#!/usr/bin/env bash
# register-action.sh — регистрирует Claude-action: создаёт YAML + шлёт TG-алёрт.
#
# Использование:
#   register-action.sh <slug> "<title>" <severity> "<command_or_skill>" ["<description>"]
#
# Severity: critical / high / medium / low
# command_or_skill — что headless Claude должен выполнить (один-shot prompt)
#
# Создаёт:
#   ~/artvision-data/actions/<YYYY-MM-DD>-<slug>.yaml
# Шлёт алёрт в TG личку Антону через tg-send.sh:
#   "<title>\nОтветь в TG: /do <action_id>"

set -euo pipefail

SLUG="${1:?slug required}"
TITLE="${2:?title required}"
SEVERITY="${3:-medium}"
COMMAND="${4:?command required}"
DESCRIPTION="${5:-}"

DATE=$(date +%Y-%m-%d)
ACTION_ID="${DATE}-${SLUG}"
ACTIONS_DIR="$HOME/artvision-data/actions"
YAML_PATH="$ACTIONS_DIR/${ACTION_ID}.yaml"

mkdir -p "$ACTIONS_DIR" "$ACTIONS_DIR/templates" "$ACTIONS_DIR/completed" "$ACTIONS_DIR/expired" "$ACTIONS_DIR/logs"

CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EXPIRES=$(date -u -v+24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "+24 hours" +%Y-%m-%dT%H:%M:%SZ)

cat > "$YAML_PATH" << YAMLEOF
id: ${ACTION_ID}
title: ${TITLE}
severity: ${SEVERITY}
description: |
  ${DESCRIPTION}
command_or_prompt: |
  ${COMMAND}
status: pending
created_at: ${CREATED}
expires_at: ${EXPIRES}
YAMLEOF

# Алёрт в TG
ICON="🟡"
case "$SEVERITY" in
    critical) ICON="🔴" ;;
    high) ICON="🟠" ;;
    medium) ICON="🟡" ;;
    low) ICON="🟢" ;;
esac

ALERT_TEXT="${ICON} ${TITLE}

${DESCRIPTION}

Чтобы запустить — ответь в этом чате:
/do ${ACTION_ID}

⏰ Действие истечёт через 24ч"

if [[ -x "$HOME/.claude/scripts/tg-send.sh" ]]; then
    "$HOME/.claude/scripts/tg-send.sh" anton "$ALERT_TEXT" 2>&1 | tail -3 || echo "(tg-send failed, action зарегистрирован)"
else
    echo "WARN: tg-send.sh не найден. Action создан, алерт не отправлен."
fi

echo "✓ Action registered: $YAML_PATH"
echo "  Trigger: /do ${ACTION_ID}"
