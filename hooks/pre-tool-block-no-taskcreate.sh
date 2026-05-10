#!/usr/bin/env bash
# pre-tool-block-no-taskcreate.sh — Layer 2 enforcement TaskCreate.
#
# Блокирует Write/Edit/Agent/MCP-write/Bash-mutating пока не вызван TaskCreate
# при наличии pending TODO > 0.
#
# Прецедент: self-corrections.md #9 (TaskCreate skip 18-19.04 при 180 pending,
# Layer 1 = SessionStart + UserPromptSubmit мягкие reminders, не сработали).
# Антон в handover 2026-04-27 явно потребовал жёсткую блокировку.
#
# Whitelist (пропуск):
#   - Task* (TaskCreate/TaskList/TaskGet/TaskUpdate/TaskOutput/TaskStop)
#   - Read-only: Read, Grep, Glob
#   - Инфра: ToolSearch, Skill, ScheduleWakeup, AskUserQuestion, EnterPlanMode/ExitPlanMode
#   - Bash для read-only команд (git status|pull|fetch|log|diff|show|branch|remote,
#     ls, pwd, cat, head, tail, grep, find, wc, echo, date, which, env, jq, python3 -c)
#
# Self-disable:
#   - после первого TaskCreate (touch /tmp/taskcreate-done-{session_id})
#   - если в transcript уже есть "name":"TaskCreate"
#
# Bypass: TASKCREATE_FORCE=1
#
# Exit codes:
#   0 = пропуск (whitelist, нет pending, уже сделан TaskCreate, bypass)
#   2 = блок (stderr → Claude увидит и вызовет TaskCreate)

set -uo pipefail

# 0. Bypass
[ "${TASKCREATE_FORCE:-0}" = "1" ] && exit 0

# 1. Read JSON stdin
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# 2. Parse session_id, tool_name, bash_command, file_path (single python call)
PARSED=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", ""))
    print(d.get("tool_name", ""))
    ti = d.get("tool_input", {}) or {}
    print(ti.get("command", "") if d.get("tool_name") == "Bash" else "")
    print(ti.get("file_path", "") if d.get("tool_name") in ("Edit", "Write", "MultiEdit") else "")
except Exception:
    print(""); print(""); print(""); print("")
' 2>/dev/null || printf '\n\n\n\n')

SESSION_ID=$(printf '%s\n' "$PARSED" | sed -n '1p')
TOOL_NAME=$(printf '%s\n' "$PARSED" | sed -n '2p')
CMD=$(printf '%s\n' "$PARSED" | sed -n '3p')
FILE_PATH=$(printf '%s\n' "$PARSED" | sed -n '4p')

[ -z "$TOOL_NAME" ] && exit 0

# 2a. Edit/Write/MultiEdit на recap-файл текущей сессии — пропуск (разрывает дедлок
# с pre-tool-recap-goal-check.sh при первом запуске сессии).
if [ -n "$SESSION_ID" ] && [ -n "$FILE_PATH" ]; then
  RECAP_FILE_LOCAL="$HOME/artvision-data/sync/recaps/${SESSION_ID}.md"
  case "$TOOL_NAME" in
    Edit|Write|MultiEdit)
      [ "$FILE_PATH" = "$RECAP_FILE_LOCAL" ] && exit 0
      ;;
  esac
fi

# 3. Whitelist tool names
case "$TOOL_NAME" in
  TaskCreate|TaskList|TaskGet|TaskUpdate|TaskOutput|TaskStop|\
  Read|Grep|Glob|\
  ToolSearch|Skill|ScheduleWakeup|AskUserQuestion|\
  EnterPlanMode|ExitPlanMode|\
  ListMcpResourcesTool|ReadMcpResourceTool)
    if [ "$TOOL_NAME" = "TaskCreate" ] && [ -n "$SESSION_ID" ]; then
      touch "/tmp/taskcreate-done-$SESSION_ID" 2>/dev/null || true
    fi
    exit 0
    ;;
esac

# 4. Self-disable если уже зафиксирован TaskCreate
if [ -n "$SESSION_ID" ] && [ -f "/tmp/taskcreate-done-$SESSION_ID" ]; then
  exit 0
fi

# 5. Bash read-only allowlist
if [ "$TOOL_NAME" = "Bash" ] && [ -n "$CMD" ]; then
  # Первая команда (до пайпов/&&/;) — для безопасной классификации
  FIRST=$(printf '%s' "$CMD" | sed -e 's/^[[:space:]]*//' | awk -F'[[:space:]|;&]' '{print $1}')
  case "$FIRST" in
    git)
      # Allow only read-only git subcommands
      SUB=$(printf '%s' "$CMD" | awk '{print $2}')
      case "$SUB" in
        status|pull|fetch|log|diff|show|branch|remote|config|stash|describe|ls-files|ls-tree|rev-parse|reflog|blame)
          exit 0 ;;
      esac
      ;;
    ls|pwd|cat|head|tail|grep|find|wc|echo|date|which|env|jq|file|du|df|stat|tree|tr|cut|sort|uniq|awk|sed|column|printf|whoami|hostname|uname|test|true|false|sleep)
      exit 0 ;;
    python3|python)
      # Только -c строки (read-only типа json.load)
      if printf '%s' "$CMD" | grep -qE '^[[:space:]]*python3?[[:space:]]+-c[[:space:]]'; then
        exit 0
      fi
      ;;
    curl)
      # GET/HEAD без -X DELETE/PUT/POST
      if ! printf '%s' "$CMD" | grep -qE '\-X[[:space:]]+(POST|PUT|DELETE|PATCH)|--data|--upload-file'; then
        exit 0
      fi
      ;;
    ssh|scp|rsync)
      # SSH без выполнения мутирующих команд — разрешим только безарг ssh host 'git status|log'
      if printf '%s' "$CMD" | grep -qE "ssh[[:space:]]+[^']+'(git[[:space:]]+(status|log|diff|fetch|show)|ls|pwd|cat|head|tail)"; then
        exit 0
      fi
      ;;
  esac
fi

# 6. Подсчёт pending TODO
PENDING=0
for f in "$HOME/artvision-data/TODO.md" \
         "$HOME/artvision-data/presale/TODO.md" \
         "$HOME/artvision-data/products/TODO.md" \
         "$HOME/artvision-tg-bot/TODO.md" \
         "$HOME/devops-agent/TODO.md"; do
  [ -f "$f" ] || continue
  n=$(grep -cE '^[[:space:]]*-[[:space:]]*\[[[:space:]]*\]' "$f" 2>/dev/null | tr -d ' ' || echo 0)
  PENDING=$((PENDING + ${n:-0}))
done

# Нет pending → пропуск
[ "$PENDING" -eq 0 ] && exit 0

# 7. Проверка transcript на наличие TaskCreate
if [ -n "$SESSION_ID" ]; then
  TRANSCRIPT=$(find "$HOME/.claude/projects" -maxdepth 3 -name "${SESSION_ID}.jsonl" 2>/dev/null | head -1)
  if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
    if grep -q '"name":"TaskCreate"' "$TRANSCRIPT" 2>/dev/null; then
      touch "/tmp/taskcreate-done-$SESSION_ID" 2>/dev/null || true
      exit 0
    fi
  fi
fi

# 8. BLOCK
{
  echo ""
  echo "⛔ pre-tool-block-no-taskcreate: ЗАБЛОКИРОВАНО"
  echo ""
  echo "Pending TODO: $PENDING. TaskCreate ещё не вызван в этой сессии."
  echo "Запрошенный инструмент: $TOOL_NAME"
  echo ""
  echo "ДЕЙСТВИЕ: вызови TaskCreate ТОЛЬКО для задачи(-ач) текущей сессии — не копируй сюда"
  echo "          общий backlog из TODO.md/Asana. Pending счётчик ($PENDING) = просто триггер,"
  echo "          а не список того что надо делать сейчас."
  echo ""
  echo "Whitelist (работают всегда):"
  echo "  • Task* (TaskCreate/TaskList/TaskGet/TaskUpdate)"
  echo "  • Read, Grep, Glob"
  echo "  • ToolSearch, Skill, ScheduleWakeup, AskUserQuestion"
  echo "  • Bash для read-only: git status|pull|fetch|log|diff, ls/pwd/cat/head/tail/grep/find/wc"
  echo ""
  echo "Bypass (на свой риск): TASKCREATE_FORCE=1 <операция>"
  echo "Прецедент: self-corrections.md #9 (TaskCreate skip 18-19.04 при 180 pending)"
} >&2

exit 2
