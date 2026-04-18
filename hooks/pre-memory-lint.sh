#!/bin/bash
# Pre-commit / pre-push hook: блокирует если memory-lint находит CRITICAL
# Запускается через PreToolUse при Bash(git commit/push)
set -euo pipefail

CMD="${1:-}"

# Активируем только на git commit/push
if [[ ! "$CMD" =~ git\ (commit|push) ]]; then
    exit 0
fi

LINT_SCRIPT="/Users/antonk/artvision-data/scripts/memory-lint.py"
[ -x "$LINT_SCRIPT" ] || exit 0

# Проверяем — есть ли изменения в memory/ или MEMORY.md в staged файлах
STAGED=$(git diff --cached --name-only 2>/dev/null || true)
if ! echo "$STAGED" | grep -qE "(memory/|MEMORY\.md)"; then
    exit 0
fi

RESULT=$(python3 "$LINT_SCRIPT" --json 2>/dev/null || echo '{"critical":[]}')
CRITICAL_COUNT=$(echo "$RESULT" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('critical',[])))" 2>/dev/null || echo 0)

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "🚫 memory-lint: $CRITICAL_COUNT CRITICAL issues" >&2
    python3 "$LINT_SCRIPT" 2>&1 | grep -A 20 "CRITICAL" | head -25 >&2
    echo "" >&2
    echo "Fix: python3 $LINT_SCRIPT --fix-orphans" >&2
    exit 1
fi

exit 0
