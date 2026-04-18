#!/usr/bin/env bash
# Post-deploy QA smoke test runner.
# Called after successful deploy (from deploy scripts like deploy-tvorims.sh).
# Runs qa-pipeline --smoke. Alerts TG on failure.
#
# Usage from deploy scripts:
#   ~/.claude/hooks/post-deploy-qa-smoke.sh <project_path> [--rollback "cmd"]
#
# Difference vs post-deploy-smoke.sh:
#   post-deploy-smoke.sh   — старый PostToolUse hook для Claude Code (триггер на scp/pm2)
#   post-deploy-qa-smoke.sh — standalone, вызывается из самих deploy-скриптов
#
# Exit:
#   0 = passed (deploy confirmed)
#   1 = failed (rollback recommended)
#   2 = misconfigured

set -euo pipefail

PROJECT_PATH="${1:-}"
ROLLBACK_CMD=""
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rollback) ROLLBACK_CMD="$2"; shift 2;;
    *) shift;;
  esac
done

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
LOG_DIR="$HOME/.claude/logs/deploy-smoke"
mkdir -p "$LOG_DIR"

if [[ -z "$PROJECT_PATH" || ! -d "$PROJECT_PATH" ]]; then
  echo "❌ Project path required: $0 <path>" >&2
  exit 2
fi

PROJECT_NAME="$(basename "$PROJECT_PATH")"
LOG_FILE="$LOG_DIR/${TIMESTAMP}_${PROJECT_NAME}.log"

DETECT="$HOME/.claude/skills/qa-pipeline/scripts/detect-project-type.sh"
PROJECT_TYPE="unknown"
[[ -x "$DETECT" ]] && PROJECT_TYPE="$("$DETECT" "$PROJECT_PATH" 2>/dev/null || echo unknown)"

{
  echo "=========================================="
  echo "QA smoke — $PROJECT_NAME ($PROJECT_TYPE)"
  echo "Time: $TIMESTAMP"
  echo "=========================================="
} | tee -a "$LOG_FILE"

cd "$PROJECT_PATH"
PASS=1

# Phase 1: Syntax
echo "[1/4] Syntax check" | tee -a "$LOG_FILE"
case "$PROJECT_TYPE" in
  telegram-bot-python|python-generic|web-scraper|api|cli|data-pipeline)
    PY=".venv/bin/python3"
    [[ -x "$PY" ]] || PY="python3"
    MAIN=$(ls bot.py main.py app.py src/main.py src/bot.py 2>/dev/null | head -1)
    if [[ -n "$MAIN" ]] && $PY -m py_compile "$MAIN" 2>>"$LOG_FILE"; then
      echo "  OK: $MAIN" | tee -a "$LOG_FILE"
    elif [[ -n "$MAIN" ]]; then
      echo "  FAIL: syntax in $MAIN" | tee -a "$LOG_FILE"; PASS=0
    fi
    ;;
  telegram-bot-typescript|web-app|node-generic)
    if [[ -f "tsconfig.json" ]] && npx tsc --noEmit 2>>"$LOG_FILE"; then
      echo "  OK: tsc" | tee -a "$LOG_FILE"
    elif [[ -f "tsconfig.json" ]]; then
      echo "  FAIL: tsc" | tee -a "$LOG_FILE"; PASS=0
    fi
    ;;
esac

# Phase 2: Unit tests (fast, -x stops on first fail)
echo "[2/4] Unit tests (smoke)" | tee -a "$LOG_FILE"
if [[ -d "tests/unit" || -d "tests" ]]; then
  case "$PROJECT_TYPE" in
    telegram-bot-python|python-generic|web-scraper|api|cli|data-pipeline)
      PY=".venv/bin/python3"
      [[ -x "$PY" ]] || PY="python3"
      if $PY -m pytest tests/ -x --tb=line -q --timeout=30 2>>"$LOG_FILE" | tail -3 | tee -a "$LOG_FILE"; then
        echo "  OK: unit pass" | tee -a "$LOG_FILE"
      else
        echo "  FAIL: unit tests" | tee -a "$LOG_FILE"; PASS=0
      fi
      ;;
  esac
else
  echo "  SKIP: no tests/" | tee -a "$LOG_FILE"
fi

# Phase 3: Process alive (LaunchAgent/PM2)
echo "[3/4] Process health" | tee -a "$LOG_FILE"
LA_LABEL="pro.artvision.${PROJECT_NAME}"
if launchctl list 2>/dev/null | grep -q "$LA_LABEL"; then
  PID=$(launchctl list | grep "$LA_LABEL" | awk '{print $1}')
  EXITCODE=$(launchctl list | grep "$LA_LABEL" | awk '{print $2}')
  if [[ "$PID" != "-" && "$EXITCODE" == "0" ]]; then
    echo "  OK: LaunchAgent PID=$PID" | tee -a "$LOG_FILE"
  else
    echo "  FAIL: LaunchAgent PID=$PID exit=$EXITCODE" | tee -a "$LOG_FILE"; PASS=0
  fi
fi

# Phase 4: Recent log errors
echo "[4/4] Recent errors check" | tee -a "$LOG_FILE"
ERR_COUNT=0
shopt -s nullglob
for lf in bot.log bot.error.log logs/*.log *.log; do
  [[ -f "$lf" ]] || continue
  RECENT=$(find "$lf" -mmin -2 2>/dev/null || true)
  if [[ -n "$RECENT" ]]; then
    C=$(tail -200 "$lf" 2>/dev/null | grep -cE "(ERROR|CRITICAL|Traceback|FATAL)" || true)
    ERR_COUNT=$((ERR_COUNT + C))
  fi
done
shopt -u nullglob
if [[ "$ERR_COUNT" -gt 5 ]]; then
  echo "  WARN: $ERR_COUNT errors in recent logs" | tee -a "$LOG_FILE"
else
  echo "  OK: $ERR_COUNT errors" | tee -a "$LOG_FILE"
fi

echo "==========================================" | tee -a "$LOG_FILE"
if [[ "$PASS" == "1" ]]; then
  echo "✅ SMOKE PASSED — $PROJECT_NAME" | tee -a "$LOG_FILE"
  exit 0
fi

echo "❌ SMOKE FAILED — $PROJECT_NAME" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"

# TG alert
TG="$HOME/.claude/scripts/tg-send.sh"
if [[ -x "$TG" ]]; then
  "$TG" team "🚨 Post-deploy smoke FAILED — \`$PROJECT_NAME\` ($PROJECT_TYPE)
Log: \`$LOG_FILE\`" 2>/dev/null || true
fi

if [[ -n "$ROLLBACK_CMD" ]]; then
  echo "Rolling back: $ROLLBACK_CMD" | tee -a "$LOG_FILE"
  eval "$ROLLBACK_CMD" 2>&1 | tee -a "$LOG_FILE" || true
fi

exit 1
