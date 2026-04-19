#!/usr/bin/env bash
# pre-push-qa-check.sh — блокирует git push если qa-full.sh существует и FAIL.
#
# Подключается в ~/.claude/settings.json как PreToolUse(Bash) хук.
# Ищет qa-full.sh в корне репо или в scripts/ — если найден, запускает.
#
# Exit codes:
#  0 = PASS или qa-full.sh не найден (пропуск)
#  1 = FAIL (git push блокируется)

set -uo pipefail

# Работаем только с `git push` — иначе пропуск
# Команда приходит в $1 (как в других хуках этого проекта) или через $CLAUDE_BASH_COMMAND env
CMD_LINE="${1:-${CLAUDE_BASH_COMMAND:-}}"
if [ -z "$CMD_LINE" ] || ! echo "$CMD_LINE" | grep -qE "(^|[[:space:]]|&&)[[:space:]]*git[[:space:]]+push"; then
  exit 0
fi

# Найти qa-full.sh (в корне репо или в scripts/, vps-bot/scripts/)
QA_SCRIPT=""
for candidate in "$(pwd)/qa-full.sh" "$(pwd)/scripts/qa-full.sh" "$(pwd)/vps-bot/scripts/qa-full.sh"; do
  [ -x "$candidate" ] && QA_SCRIPT="$candidate" && break
done

if [ -z "$QA_SCRIPT" ]; then
  # qa-full.sh не настроен для этого репо — пропуск
  exit 0
fi

echo "🔍 pre-push QA: $QA_SCRIPT" >&2
if bash "$QA_SCRIPT" > /tmp/qa-pre-push.log 2>&1; then
  echo "✅ QA PASS — push разрешён" >&2
  exit 0
else
  echo "❌ QA FAILED — git push заблокирован" >&2
  echo "Подробности: /tmp/qa-pre-push.log" >&2
  tail -20 /tmp/qa-pre-push.log >&2
  echo "" >&2
  echo "Fix и повтори, или: QA_SKIP=1 git push (на свой риск)" >&2
  # Bypass для экстренных случаев
  [ "${QA_SKIP:-0}" = "1" ] && { echo "⚠ QA_SKIP=1 — push разрешён несмотря на FAIL" >&2; exit 0; }
  exit 1
fi
