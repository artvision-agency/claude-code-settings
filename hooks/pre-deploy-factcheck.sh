#!/bin/bash
set -euo pipefail

# Pre-deploy factcheck hook
# Triggered: before scp to VPS for files in clients/*/
# Blocks deployment if CRITICAL issues found
#
# Usage as hook:   CLAUDE_BASH_COMMAND="scp file.html root@80.90.181.152:/path" ./pre-deploy-factcheck.sh
# Usage direct:    ./pre-deploy-factcheck.sh <file.html> [--force]
# Usage PreToolUse: intercepts Bash commands containing 'scp' + '.html' + VPS IP

VPS_IP="80.90.181.152"
FACTCHECK_SCRIPT="/Users/antonk/.claude/scripts/factcheck-v2.py"
FACTCHECK_LEGACY="/Users/antonk/artvision-data/scripts/factcheck-html.py"

# --- Determine mode: hook (CLAUDE_BASH_COMMAND) or direct invocation ---

FORCE=0
FILE=""

if [ -n "${CLAUDE_BASH_COMMAND:-}" ]; then
    # Hook mode: intercept scp commands
    COMMAND="$CLAUDE_BASH_COMMAND"

    # Only trigger on scp with HTML files to our VPS
    if ! echo "$COMMAND" | grep -qE "scp\s+.*\.html.*${VPS_IP}"; then
        exit 0
    fi

    # Extract HTML file from scp command
    FILE=$(echo "$COMMAND" | grep -oE '[^ ]+\.html' | head -1)

    # Check for --force in the command
    echo "$COMMAND" | grep -q -- '--force' && FORCE=1
else
    # Direct invocation mode
    FILE="${1:-}"
    shift 2>/dev/null || true

    # Parse remaining args
    for arg in "$@"; do
        case "$arg" in
            --force) FORCE=1 ;;
        esac
    done
fi

# No file found — nothing to check
if [ -z "$FILE" ]; then
    exit 0
fi

# Only check HTML files in clients/
if [[ ! "$FILE" =~ clients/.*/.*\.html$ ]]; then
    # Not a client HTML file — still run basic check if it's any HTML
    if [[ ! "$FILE" =~ \.html$ ]]; then
        exit 0
    fi
fi

# File must exist
if [ ! -f "$FILE" ]; then
    echo "WARNING: File not found: $FILE — skipping factcheck"
    exit 0
fi

# Factcheck script must exist
if [ ! -f "$FACTCHECK_SCRIPT" ]; then
    echo "WARNING: Factcheck script not found: $FACTCHECK_SCRIPT"
    echo "Deployment will proceed without factcheck."
    exit 0
fi

# --- Extract client name from path ---
CLIENT="unknown"
if [[ "$FILE" =~ clients/([^/]+)/ ]]; then
    CLIENT="${BASH_REMATCH[1]}"
fi

CLIENT_DIR="$(cd "$(dirname "$FILE")" && pwd)"

# --- Find source files for cross-reference ---
SOURCES=""
if [ -f "$CLIENT_DIR/config.yaml" ]; then
    SOURCES="$SOURCES --source $CLIENT_DIR/config.yaml"
fi

# Check for corrections log
for corrections in "$CLIENT_DIR"/patches/corrections-log-*.md; do
    if [ -f "$corrections" ]; then
        SOURCES="$SOURCES --source $corrections"
    fi
done

# Check for context log
if [ -f "$CLIENT_DIR/context-log.md" ]; then
    SOURCES="$SOURCES --source $CLIENT_DIR/context-log.md"
fi

echo "======================================="
echo "  FACTCHECK PRE-DEPLOY: $CLIENT"
echo "======================================="
echo "  File: $FILE"
echo "  Force: $( [ $FORCE -eq 1 ] && echo 'YES (bypass)' || echo 'no' )"
echo "======================================="

# --- Run factcheck ---
REPORT="/tmp/factcheck-${CLIENT}-$(date +%Y%m%d-%H%M%S).md"

# Determine base URL from scp target path
BASE_URL=""
if [ -n "${CLAUDE_BASH_COMMAND:-}" ]; then
    REMOTE_PATH=$(echo "$CLAUDE_BASH_COMMAND" | grep -oE "${VPS_IP}:[^ ]+" | sed "s/${VPS_IP}://" | sed 's|/var/www/artvision/|https://artvision.pro/|')
    if [ -n "$REMOTE_PATH" ]; then
        BASE_URL="--base-url $(dirname "$REMOTE_PATH")"
    fi
fi

# Try factcheck-v2, fallback to legacy
FACTCHECK_EXIT=0
if [ -f "$FACTCHECK_SCRIPT" ]; then
    if python3 "$FACTCHECK_SCRIPT" "$FILE" $SOURCES $BASE_URL --report "$REPORT" --standard 2>&1; then
        FACTCHECK_EXIT=0
    else
        FACTCHECK_EXIT=$?
    fi
elif [ -f "$FACTCHECK_LEGACY" ]; then
    if python3 "$FACTCHECK_LEGACY" "$FILE" $SOURCES 2>&1 | tee "$REPORT"; then
        FACTCHECK_EXIT=0
    else
        FACTCHECK_EXIT=$?
    fi
else
    echo "WARNING: No factcheck script found"
    exit 0
fi

echo ""

if [ $FACTCHECK_EXIT -ne 0 ]; then
    if [ $FORCE -eq 1 ]; then
        echo "WARNING: FACTCHECK FAILED but --force flag used"
        echo "   Deployment will proceed. Report: $REPORT"
        echo "======================================="
        exit 0
    else
        echo "FACTCHECK FAILED -- deployment BLOCKED"
        echo "   Report: $REPORT"
        echo ""
        echo "   To bypass: add --force flag"
        echo "   To fix: review report and correct data sources"
        echo "======================================="
        exit 1
    fi
else
    # --- Semantic factcheck reminder (cannot be automated) ---
    SEMANTIC_MARKER="/tmp/factcheck-semantic-${CLIENT}-$(date +%Y%m%d).done"
    if [ ! -f "$SEMANTIC_MARKER" ]; then
        echo ""
        echo "======================================="
        echo "  ⚠️  СМЫСЛОВОЙ ФАКТЧЕКИНГ НЕ ПРОЙДЕН"
        echo "======================================="
        echo "  URL и структура ОК, но числа и факты"
        echo "  НЕ проверены автоматически."
        echo ""
        echo "  Чеклист перед отправкой клиенту:"
        echo "  □ Числа проверены через 2+ источника?"
        echo "  □ Конкуренты реальные (не выдуманные)?"
        echo "  □ URL картинок взяты с реального сайта?"
        echo "  □ Источники кликабельны и доступны?"
        echo ""
        echo "  Чтобы подтвердить:"
        echo "    touch $SEMANTIC_MARKER"
        echo "  Или: /factcheck --strict (агент проверит)"
        echo "======================================="
        exit 1
    else
        echo "FACTCHECK PASSED (URL + semantic)"
        echo "   Report: $REPORT"
        echo "   Semantic: confirmed $(date -r "$SEMANTIC_MARKER" '+%H:%M')"
        echo "======================================="
        exit 0
    fi
fi
