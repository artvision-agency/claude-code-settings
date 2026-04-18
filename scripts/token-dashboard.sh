#!/usr/bin/env bash
set -euo pipefail

TOOL_DIR="$HOME/artvision-data/tools/claude-usage"

if [[ ! -f "$TOOL_DIR/cli.py" ]]; then
    echo "ERROR: claude-usage tool not found at $TOOL_DIR"
    exit 1
fi

CMD="${1:-dashboard}"

case "$CMD" in
    report)
        python3 "$TOOL_DIR/cli.py" scan
        python3 "$TOOL_DIR/cli.py" today
        python3 "$TOOL_DIR/cli.py" stats
        ;;
    dashboard|today|stats|scan)
        python3 "$TOOL_DIR/cli.py" "$CMD"
        ;;
    *)
        echo "Usage: token-dashboard.sh [report|dashboard|today|stats|scan]"
        exit 1
        ;;
esac
