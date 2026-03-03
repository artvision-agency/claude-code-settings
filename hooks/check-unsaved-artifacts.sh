#!/bin/bash
# Check for unsaved artifacts from claude.ai on session start
# Looks for recent HTML/MD files in Downloads that might need saving to git

DOWNLOADS="$HOME/Downloads"
ARTVISION="$HOME/artvision-data/clients"
HOURS=72  # Check files from last 72 hours

# Find recent HTML/MD files in Downloads
RECENT_FILES=$(find "$DOWNLOADS" -maxdepth 1 \( -name "*.html" -o -name "*.md" \) -mtime -3 2>/dev/null | sort -t/ -k$(echo "$DOWNLOADS" | tr -cd '/' | wc -c | tr -d ' ')d)

# Check Asana for pending "save to git" tasks
PENDING_SAVES=""

if [ -n "$RECENT_FILES" ]; then
    COUNT=$(echo "$RECENT_FILES" | wc -l | tr -d ' ')

    # Check which are NOT yet in artvision-data
    UNSAVED=""
    while IFS= read -r file; do
        BASENAME=$(basename "$file")
        # Search in clients/ folders
        if ! find "$ARTVISION" -name "$BASENAME" -print -quit 2>/dev/null | grep -q .; then
            UNSAVED="$UNSAVED\n  - $BASENAME"
        fi
    done <<< "$RECENT_FILES"

    if [ -n "$UNSAVED" ]; then
        echo "# Unsaved Artifacts from claude.ai"
        echo ""
        echo "Found files in Downloads NOT yet in git:"
        echo -e "$UNSAVED"
        echo ""
        echo "Use /save-from-chat to save them, or /save-from-chat --scan to auto-detect."
    fi
fi
