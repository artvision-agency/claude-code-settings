#!/bin/bash
# Восстановление контекста при старте сессии Claude Code
# Запускается как SessionStart hook
# Собирает: git pull, коммиты с VDS/TG, незавершённые задачи, контекст
set -euo pipefail

# ─── Конфигурация ───
REPOS=(
  "$HOME/artvision-data"
  "$HOME/artvision-tg-bot"
  "$HOME/devops-agent"
)
SYNC_STATUS="$HOME/artvision-data/sync/SYNC_STATUS.md"
SESSION_STATE="$HOME/artvision-data/sync/SESSION_STATE.json"
LAST_SESSION_FILE="$HOME/.claude/.last_local_session"

# ─── Определяем время последней локальной сессии ───
if [ -f "$LAST_SESSION_FILE" ]; then
  LAST_SESSION=$(cat "$LAST_SESSION_FILE")
else
  # Первый запуск — берём 24 часа назад
  LAST_SESSION=$(date -v-24H "+%Y-%m-%dT%H:%M:%S" 2>/dev/null || date -d "24 hours ago" "+%Y-%m-%dT%H:%M:%S" 2>/dev/null || echo "")
fi

# Сохраняем текущее время как последнюю сессию
date "+%Y-%m-%dT%H:%M:%S" > "$LAST_SESSION_FILE"

# ─── Форматируем дату для отображения ───
if [ -n "$LAST_SESSION" ]; then
  # macOS date
  LAST_SESSION_DISPLAY=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$LAST_SESSION" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "$LAST_SESSION")
else
  LAST_SESSION_DISPLAY="неизвестно"
  LAST_SESSION=$(date -v-24H "+%Y-%m-%dT%H:%M:%S" 2>/dev/null || echo "2026-01-01T00:00:00")
fi

# ─── Git pull все репо (тихо, ошибки не фатальны) ───
PULL_RESULTS=""
for repo in "${REPOS[@]}"; do
  if [ -d "$repo/.git" ]; then
    REPO_NAME=$(basename "$repo")
    PULL_OUT=$(cd "$repo" && git pull --ff-only 2>&1) || PULL_OUT=$(cd "$repo" && git pull --rebase 2>&1) || PULL_OUT="pull failed"
    if echo "$PULL_OUT" | grep -q "Already up to date"; then
      : # молчим
    elif echo "$PULL_OUT" | grep -q "pull failed"; then
      PULL_RESULTS="${PULL_RESULTS}  ⚠️ ${REPO_NAME}: pull failed\n"
    else
      CHANGES=$(echo "$PULL_OUT" | grep -c "^" 2>/dev/null || echo "?")
      PULL_RESULTS="${PULL_RESULTS}  ✅ ${REPO_NAME}: обновлён\n"
    fi
  fi
done

# ─── Собираем коммиты с момента последней сессии ───
VDS_COMMITS=""
VDS_COUNT=0
TG_COMMITS=""
TG_COUNT=0
OTHER_COMMITS=""
OTHER_COUNT=0
AUTOSYNC_COUNT=0

for repo in "${REPOS[@]}"; do
  if [ -d "$repo/.git" ]; then
    REPO_NAME=$(basename "$repo")

    # Коммиты с VDS (автор root или содержат VDS/vps в сообщении)
    while IFS= read -r line; do
      if [ -n "$line" ]; then
        VDS_COMMITS="${VDS_COMMITS}  - [${REPO_NAME}] ${line}\n"
        VDS_COUNT=$((VDS_COUNT + 1))
      fi
    done < <(cd "$repo" && git log --since="$LAST_SESSION" --oneline --all \
      --grep="VDS\|vps\|deploy\|nginx" -i 2>/dev/null | head -10)

    # Коммиты с VDS по автору (root@)
    while IFS= read -r line; do
      if [ -n "$line" ]; then
        # Проверяем что ещё не добавлен
        HASH=$(echo "$line" | cut -d' ' -f1)
        if ! echo -e "$VDS_COMMITS" | grep -q "$HASH" 2>/dev/null; then
          VDS_COMMITS="${VDS_COMMITS}  - [${REPO_NAME}] ${line}\n"
          VDS_COUNT=$((VDS_COUNT + 1))
        fi
      fi
    done < <(cd "$repo" && git log --since="$LAST_SESSION" --oneline --all \
      --author="root" 2>/dev/null | head -10)

    # Коммиты из TG-relay
    while IFS= read -r line; do
      if [ -n "$line" ]; then
        TG_COMMITS="${TG_COMMITS}  - [${REPO_NAME}] ${line}\n"
        TG_COUNT=$((TG_COUNT + 1))
      fi
    done < <(cd "$repo" && git log --since="$LAST_SESSION" --oneline --all \
      --grep="tg-relay\|voice\|telegram\|TG:" -i 2>/dev/null | head -10)

    # Значимые коммиты (не auto-sync, не chore: auto-sync)
    while IFS= read -r line; do
      if [ -n "$line" ]; then
        HASH=$(echo "$line" | cut -d' ' -f1)
        # Пропускаем уже учтённые VDS и TG
        if ! echo -e "${VDS_COMMITS}${TG_COMMITS}" | grep -q "$HASH" 2>/dev/null; then
          # Фильтруем auto-sync шум
          if echo "$line" | grep -qiE "auto-sync|chore: auto-sync on session stop"; then
            AUTOSYNC_COUNT=$((AUTOSYNC_COUNT + 1))
          else
            OTHER_COMMITS="${OTHER_COMMITS}  - [${REPO_NAME}] ${line}\n"
            OTHER_COUNT=$((OTHER_COUNT + 1))
          fi
        fi
      fi
    done < <(cd "$repo" && git log --since="$LAST_SESSION" --oneline --all 2>/dev/null | head -20)

  fi
done

TOTAL_COMMITS=$((VDS_COUNT + TG_COUNT + OTHER_COUNT + AUTOSYNC_COUNT))

# ─── Незавершённые задачи из TODO.md файлов ───
PENDING_TASKS=""
TODO_FILES=(
  "$HOME/artvision-data/TODO.md"
  "$HOME/artvision-tg-bot/TODO.md"
  "$HOME/devops-agent/TODO.md"
  "$HOME/artvision-data/presale/TODO.md"
  "$HOME/artvision-data/products/TODO.md"
)

for todo_file in "${TODO_FILES[@]}"; do
  if [ -f "$todo_file" ]; then
    CONTEXT=$(basename "$(dirname "$todo_file")")
    # macOS grep -c возвращает пустую строку при 0
    TASKS=$(grep -n '^\- \[ \]' "$todo_file" 2>/dev/null | head -5)
    if [ -n "$TASKS" ]; then
      while IFS= read -r line; do
        TASK_TEXT=$(echo "$line" | sed 's/^[0-9]*:- \[ \] //')
        PENDING_TASKS="${PENDING_TASKS}  - [ ] [${CONTEXT}] ${TASK_TEXT}\n"
      done <<< "$TASKS"
    fi
  fi
done

# ─── SESSION_STATE.json (если есть) ───
STATE_INFO=""
if [ -f "$SESSION_STATE" ]; then
  STATE_INFO=$(python3 << 'PYEOF'
import json, os
try:
    with open(os.path.expanduser("~/artvision-data/sync/SESSION_STATE.json")) as f:
        state = json.load(f)
    ctx = state.get("context", "")
    task = state.get("current_task", "")
    env = state.get("environment", "")
    branch = state.get("branch", "")
    parts = []
    if ctx: parts.append(f"Контекст: {ctx}")
    if task: parts.append(f"Задача: {task}")
    if env: parts.append(f"Среда: {env}")
    if branch: parts.append(f"Ветка: {branch}")
    if parts:
        print("\n".join(parts))
except:
    pass
PYEOF
  )
fi

# ─── Текущий контекст git ───
CURRENT_BRANCH=""
CURRENT_REPO=""
for repo in "${REPOS[@]}"; do
  if [ -d "$repo/.git" ]; then
    REPO_NAME=$(basename "$repo")
    BRANCH=$(cd "$repo" && git branch --show-current 2>/dev/null || echo "?")
    HAS_CHANGES=$(cd "$repo" && git status --porcelain 2>/dev/null | head -1)
    MARKER=""
    if [ -n "$HAS_CHANGES" ]; then
      MARKER="*"
    fi
    if [ -n "$CURRENT_BRANCH" ]; then
      CURRENT_BRANCH="${CURRENT_BRANCH}, "
    fi
    CURRENT_BRANCH="${CURRENT_BRANCH}${REPO_NAME}:${BRANCH}${MARKER}"
  fi
done

# ─── SYNC_STATUS.md (последняя дата) ───
SYNC_DATE=""
if [ -f "$SYNC_STATUS" ]; then
  SYNC_DATE=$(grep '^\*\*Date\*\*:' "$SYNC_STATUS" 2>/dev/null | head -1 | sed 's/.*: //' || echo "")
fi

# ═══════════════════════════════════════════════════════
# ВЫВОД
# ═══════════════════════════════════════════════════════

echo "# Восстановление сессии"
echo ""
echo "Последняя локальная сессия: ${LAST_SESSION_DISPLAY}"

if [ -n "$SYNC_DATE" ]; then
  echo "Последний sync: ${SYNC_DATE}"
fi

SYNC_NOTE=""
if [ "$AUTOSYNC_COUNT" -gt 0 ]; then
  SYNC_NOTE=", auto-sync: ${AUTOSYNC_COUNT}"
fi
echo "С тех пор: ${TOTAL_COMMITS} коммитов (VDS: ${VDS_COUNT}, TG: ${TG_COUNT}, значимые: ${OTHER_COUNT}${SYNC_NOTE})"
echo ""

# Pull results
if [ -n "$PULL_RESULTS" ]; then
  echo "## Git Pull"
  echo -e "$PULL_RESULTS"
fi

# VDS коммиты
if [ "$VDS_COUNT" -gt 0 ]; then
  echo "## Сделано на VDS (${VDS_COUNT}):"
  echo -e "$VDS_COMMITS"
fi

# TG коммиты
if [ "$TG_COUNT" -gt 0 ]; then
  echo "## Команды из TG (${TG_COUNT}):"
  echo -e "$TG_COMMITS"
fi

# Значимые коммиты
if [ "$OTHER_COUNT" -gt 0 ]; then
  echo "## Значимые коммиты (${OTHER_COUNT}):"
  echo -e "$OTHER_COMMITS"
fi

# Незавершённые задачи
if [ -n "$PENDING_TASKS" ]; then
  echo "## Незавершённые задачи:"
  echo -e "$PENDING_TASKS"
else
  echo "## Незавершённые задачи: нет открытых [ ] в TODO.md"
  echo ""
fi

# SESSION_STATE
if [ -n "$STATE_INFO" ]; then
  echo "## Сохранённое состояние:"
  echo "$STATE_INFO"
  echo ""
fi

# Недавние TG-отправки (из sync/HANDOFF_*.md)
HANDOFF_DIR="$HOME/artvision-data/sync"
if [ -d "$HANDOFF_DIR" ]; then
  # Последние 2 HANDOFF файла
  RECENT_HANDOFFS=$(ls -t "$HANDOFF_DIR"/HANDOFF_*.md 2>/dev/null | head -2)
  if [ -n "$RECENT_HANDOFFS" ]; then
    TG_LOG=""
    while IFS= read -r hf; do
      DATE_PART=$(basename "$hf" .md | sed 's/HANDOFF_//')
      LINES=$(grep -E '^- [0-9]{2}:[0-9]{2}:[0-9]{2}Z \| channel=' "$hf" 2>/dev/null | tail -5)
      if [ -n "$LINES" ]; then
        TG_LOG="${TG_LOG}\n### ${DATE_PART}\n${LINES}\n"
      fi
    done <<< "$RECENT_HANDOFFS"
    if [ -n "$TG_LOG" ]; then
      echo "## Недавние TG-отправки:"
      echo -e "$TG_LOG"
      echo ""
    fi
  fi
fi

# Текущие ветки
echo "## Репозитории: ${CURRENT_BRANCH}"
echo ""
