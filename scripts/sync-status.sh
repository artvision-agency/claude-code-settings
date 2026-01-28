#!/bin/bash
# Claude Sync Status Helper
# Использование: sync-status.sh [pull|push|status]

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
SYNC_FILE="$PROJECT_ROOT/sync/SYNC_STATUS.md"

if [ -z "$PROJECT_ROOT" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

if [ ! -f "$SYNC_FILE" ]; then
    # Проверяем альтернативное имя файла
    if [ -f "$PROJECT_ROOT/sync/CURRENT_CONTEXT.md" ]; then
        SYNC_FILE="$PROJECT_ROOT/sync/CURRENT_CONTEXT.md"
    else
        echo "Error: No sync file found at $SYNC_FILE"
        exit 1
    fi
fi

case "$1" in
    pull)
        echo "Pulling latest changes..."
        git pull
        echo ""
        echo "=== Current Sync Status ==="
        head -50 "$SYNC_FILE"
        ;;
    push)
        echo "Committing sync changes..."
        git add sync/
        git commit -m "sync: update session status"
        git push
        echo "Done!"
        ;;
    status)
        echo "=== Sync Status: $(basename $PROJECT_ROOT) ==="
        echo "File: $SYNC_FILE"
        echo ""
        head -30 "$SYNC_FILE"
        ;;
    *)
        echo "Claude Sync Status Helper"
        echo ""
        echo "Usage: sync-status.sh [command]"
        echo ""
        echo "Commands:"
        echo "  pull    - git pull + show sync status"
        echo "  push    - commit and push sync changes"
        echo "  status  - show current sync status"
        ;;
esac
