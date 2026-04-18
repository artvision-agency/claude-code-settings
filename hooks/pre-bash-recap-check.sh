#!/usr/bin/env bash
# pre-bash-recap-check.sh — PreToolUse(Bash) hook
# Срабатывает на `git push` — проверяет recap текущей сессии:
#  - заполнена ли "Цель сессии"
#  - есть ли незакрытые acceptance criteria
# Выводит warning в stdout (не блокирует).

set -Eeuo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Триггер только на git push
if [[ ! "$COMMAND" =~ git[[:space:]]+push ]]; then
  exit 0
fi

[[ -z "$SESSION_ID" ]] && exit 0

RECAP_FILE="$HOME/artvision-data/sync/recaps/${SESSION_ID}.md"
[[ ! -f "$RECAP_FILE" ]] && exit 0

# Проверка: заполнена ли цель?
if grep -q "_Не заполнено — ждёт первого запроса._" "$RECAP_FILE"; then
  echo "⚠️  RECAP: цель сессии НЕ заполнена. Заполни sync/recaps/${SESSION_ID}.md ПЕРЕД sync." >&2
  echo "   (push не заблокирован, но это нарушение правила recap.md)" >&2
fi

# Подсчёт незакрытых acceptance
OPEN=$(grep -c '^- \[ \]' "$RECAP_FILE" 2>/dev/null || echo 0)
DONE=$(grep -c '^- \[x\]' "$RECAP_FILE" 2>/dev/null || echo 0)

if [[ "$OPEN" -gt 0 ]]; then
  echo "⚠️  RECAP: $OPEN незакрытых пунктов в recap (закрыто $DONE)." >&2
  echo "   Покажи план/факт пользователю и спроси: дожимаем / коммитим как есть / меняем цель." >&2
fi

exit 0
