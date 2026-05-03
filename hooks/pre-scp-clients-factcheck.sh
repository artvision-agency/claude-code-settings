#!/usr/bin/env bash
# pre-scp-clients-factcheck.sh — PreToolUse Bash
#
# Блокирует scp/rsync/curl команды которые деплоят клиентские HTML-документы
# (КП, отчёты, presale) если factcheck-v2.py не был прогнан в текущей сессии.
#
# Триггеры (regex по command):
#   scp .* clients/.*\.html
#   scp .* /var/www/.*kp.* | /var/www/.*audit.*
#   rsync .* clients/.*\.html
#   curl -X (POST|PUT) .*kp.*\.html
#
# Bypass:
#   FACTCHECK_SKIP=1  (env)
#   touch /tmp/factcheck-done-{session_id} (per-session snooze)

set -uo pipefail

[[ "${FACTCHECK_SKIP:-0}" == "1" ]] && exit 0

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[[ "$TOOL_NAME" != "Bash" ]] && exit 0

CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

# Snooze
[[ -f "/tmp/factcheck-done-${SESSION_ID}" ]] && exit 0

# Triggers
TRIGGER=""
if echo "$CMD" | grep -qE '^(scp|rsync)[^|]*clients/[^/]+/.*\.html'; then
  TRIGGER="scp/rsync clients HTML"
elif echo "$CMD" | grep -qE 'scp.*(/var/www/artvision/kp/|/var/www/.*audit|/var/www/.*presale)'; then
  TRIGGER="scp в /kp//audit/presale на VPS"
elif echo "$CMD" | grep -qE 'curl[^|]+-X[[:space:]]+(POST|PUT).*\.(html|pdf)'; then
  TRIGGER="curl POST клиентский документ"
fi

[[ -z "$TRIGGER" ]] && exit 0

# Проверяем был ли factcheck-v2.py запущен в этой сессии
TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
if [[ -f "$TRANSCRIPT" ]]; then
  if grep -qE 'factcheck-v2\.py|"skill":\s*"factcheck"' "$TRANSCRIPT" 2>/dev/null; then
    exit 0  # OK, factcheck был
  fi
fi

cat >&2 <<EOF
[factcheck-required] ⛔ BLOCKED — деплой клиентского документа без factcheck

Триггер: ${TRIGGER}
Команда: ${CMD:0:120}...

Действие:
  1. Запустите Skill factcheck (или python3 factcheck-v2.py <file>)
  2. Дождитесь VERDICT: PASS или REVIEW
  3. Только потом scp/rsync/POST

Bypass (если факт-чек не нужен — например деплой статики без чисел):
  FACTCHECK_SKIP=1 ./команда
  ИЛИ touch /tmp/factcheck-done-${SESSION_ID}

Это правило защищает от отправки клиенту документа с непроверенными числами/URL.
EOF
exit 2
