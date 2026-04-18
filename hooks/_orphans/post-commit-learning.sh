#!/bin/bash
# Post-commit hook: собирает сигналы обучения после каждого коммита
# Складывает в очередь ~/.claude/learning-queue/
# Claude обрабатывает при старте сессии или Stop хуке
set -euo pipefail

# Защита от зацикливания: не запускать если вызвано из Claude hook
if [ -n "${CLAUDE_HOOK:-}" ] || [ -n "${GIT_LEARNING_RUNNING:-}" ]; then
    exit 0
fi
export GIT_LEARNING_RUNNING=1

# Тихий режим — не блокировать коммит при ошибках
trap 'exit 0' ERR

QUEUE_DIR="$HOME/.claude/learning-queue"
mkdir -p "$QUEUE_DIR"

REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")
COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
COMMIT_MSG=$(git log -1 --pretty=%s 2>/dev/null || echo "")
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null || echo "")
TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)

# Определяем тип сигнала
SIGNAL_TYPE=""
SIGNAL_DETAIL=""

# 1. Fix коммиты
if echo "$COMMIT_MSG" | grep -iqE '^fix[:(]|bugfix|hotfix'; then
    SIGNAL_TYPE="error_resolution"
    SIGNAL_DETAIL="$COMMIT_MSG"
fi

# 2. Новые хуки/скрипты
HOOK_FILES=$(echo "$CHANGED_FILES" | grep -E '\.claude/(hooks|scripts)/' || true)
if [ -n "$HOOK_FILES" ]; then
    SIGNAL_TYPE="${SIGNAL_TYPE:+$SIGNAL_TYPE,}automation"
    SIGNAL_DETAIL="${SIGNAL_DETAIL:+$SIGNAL_DETAIL | }hooks: $(echo "$HOOK_FILES" | xargs -I{} basename {} | tr '\n' ', ')"
fi

# 3. Новые правила
RULE_FILES=$(echo "$CHANGED_FILES" | grep -E '\.claude/rules/|rules/' || true)
if [ -n "$RULE_FILES" ]; then
    SIGNAL_TYPE="${SIGNAL_TYPE:+$SIGNAL_TYPE,}rule_update"
    SIGNAL_DETAIL="${SIGNAL_DETAIL:+$SIGNAL_DETAIL | }rules: $(echo "$RULE_FILES" | xargs -I{} basename {} | tr '\n' ', ')"
fi

# 4. Новые скиллы
SKILL_FILES=$(echo "$CHANGED_FILES" | grep -E '\.claude/skills/' | grep -v 'learned/' || true)
if [ -n "$SKILL_FILES" ]; then
    SIGNAL_TYPE="${SIGNAL_TYPE:+$SIGNAL_TYPE,}new_skill"
    SIGNAL_DETAIL="${SIGNAL_DETAIL:+$SIGNAL_DETAIL | }skills: $(echo "$SKILL_FILES" | xargs -I{} basename {} | tr '\n' ', ')"
fi

# 5. Memory feedback/lessons
MEMORY_FILES=$(echo "$CHANGED_FILES" | grep -E 'memory/(feedback_|lessons)' || true)
if [ -n "$MEMORY_FILES" ]; then
    SIGNAL_TYPE="${SIGNAL_TYPE:+$SIGNAL_TYPE,}lesson_learned"
    SIGNAL_DETAIL="${SIGNAL_DETAIL:+$SIGNAL_DETAIL | }memory: $(echo "$MEMORY_FILES" | xargs -I{} basename {} | tr '\n' ', ')"
fi

# 6. Workarounds в коде (grep diff)
WORKAROUND=$(git diff HEAD~1..HEAD 2>/dev/null | grep '^+' | grep -iE 'workaround|hack|FIXME|fallback|retry' | head -1 || true)
if [ -n "$WORKAROUND" ]; then
    SIGNAL_TYPE="${SIGNAL_TYPE:+$SIGNAL_TYPE,}workaround"
    SIGNAL_DETAIL="${SIGNAL_DETAIL:+$SIGNAL_DETAIL | }workaround: ${WORKAROUND:0:100}"
fi

# Если есть сигналы — записать в очередь
if [ -n "$SIGNAL_TYPE" ]; then
    QUEUE_FILE="$QUEUE_DIR/${TIMESTAMP}_${REPO_NAME}_${COMMIT_HASH}.json"
    cat > "$QUEUE_FILE" << JSONEOF
{
  "timestamp": "$TIMESTAMP",
  "repo": "$REPO_NAME",
  "commit": "$COMMIT_HASH",
  "message": $(python3 -c "import json; print(json.dumps('$COMMIT_MSG'))" 2>/dev/null || echo "\"$COMMIT_MSG\""),
  "signal_type": "$SIGNAL_TYPE",
  "detail": $(python3 -c "import json; print(json.dumps('$SIGNAL_DETAIL'))" 2>/dev/null || echo "\"$SIGNAL_DETAIL\""),
  "files": $(echo "$CHANGED_FILES" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")
}
JSONEOF
fi

# Очистка: удалить записи старше 7 дней
find "$QUEUE_DIR" -name "*.json" -mtime +7 -delete 2>/dev/null || true
