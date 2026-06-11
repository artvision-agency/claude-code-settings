#!/bin/bash
# SessionStart hook — inject TaskCreate imperative for NEW pending TODO items.
#
# Dedupe: stores a seen-set per context in /tmp/taskcreate-seen-{ctx}.txt.
# Only NEW (unseen) items are injected; already-injected items are skipped.
# Reset the seen-set by deleting /tmp/taskcreate-seen-*.txt.
#
# Routing: sourced from ~/.claude/scripts/lib/todo-route.sh (single source).

set -euo pipefail

# Load shared routing
LIB=/Users/antonk/.claude/scripts/lib/todo-route.sh
if [ ! -f "$LIB" ]; then
    exit 0  # silent fail if lib missing (don't break session start)
fi
# shellcheck source=/dev/null
source "$LIB"

# Resolve TODO path + context
mapping="$(todo_for_cwd "${PWD:-$HOME}")"
TODO="${mapping%%$'\t'*}"
CTX="${mapping##*$'\t'}"

[ -f "$TODO" ] || exit 0

# Dedupe cache per SESSION (не per-context!) — иначе после 1-й сессии кэш в /tmp
# глушит императив для всех последующих сессий до reboot (баг: задачи «не появляются»).
# session_id из stdin SessionStart → новая сессия = свежий кэш = императив срабатывает;
# resume той же сессии (--resume сохраняет session_id) = без повторного нага.
INPUT=$(cat 2>/dev/null || echo '{}')
SESSION_ID=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','nosess'))" 2>/dev/null || echo "nosess")
# Подчистить старые per-context кэши (legacy) + чужих сессий старше суток
find /tmp -maxdepth 1 -name "taskcreate-seen-${CTX}*.txt" -mtime +1 -delete 2>/dev/null || true
SEEN=/tmp/taskcreate-seen-${CTX}-${SESSION_ID}.txt
touch "$SEEN"

# Collect pending lines, strip to stable hash-key (first 80 chars)
declare -a NEW_LINES=()
COUNT_TOTAL=0
while IFS= read -r line; do
    COUNT_TOTAL=$((COUNT_TOTAL + 1))
    key=$(printf '%s' "$line" | cut -c1-80)
    if ! grep -Fxq -- "$key" "$SEEN"; then
        NEW_LINES+=("$line")
        printf '%s\n' "$key" >> "$SEEN"
    fi
    # Cap new items to avoid context flood
    [ "${#NEW_LINES[@]}" -ge 10 ] && break
done < <(grep -E "^- \[ \]" "$TODO" 2>/dev/null || true)

# No new items → silent exit (prevents re-injection on resume)
[ "${#NEW_LINES[@]}" -eq 0 ] && exit 0

cat <<EOF
═══════════════════════════════════════════
🎯 AUTOMATIC TASKCREATE REQUIRED (context: $CTX)
═══════════════════════════════════════════
TODO file: $TODO
Всего pending: $COUNT_TOTAL | Новых к созданию: ${#NEW_LINES[@]}

ОБЯЗАТЕЛЬНОЕ ДЕЙСТВИЕ перед ответом пользователю:
Вызови TaskCreate для КАЖДОГО из следующих pending items:

EOF
printf '%s\n' "${NEW_LINES[@]}"
cat <<EOF

Это автоматика — пользователь НЕ обязан напоминать.
После TaskCreate можешь продолжать диалог.
(Seen-cache: $SEEN — удали файл чтобы сбросить.)
═══════════════════════════════════════════
EOF
exit 0
