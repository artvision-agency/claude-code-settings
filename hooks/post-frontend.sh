#!/bin/bash
# Auto-run tests after frontend-developer creates HTML
# Triggered by Write tool on .html files

FILE="$1"

if [[ "$FILE" == *.html ]]; then
    echo "🧪 Auto-testing: $FILE"

    # Run Playwright test
    if command -v node &> /dev/null; then
        node /Users/antonk/artvision-data/.claude_temp_scripts/test_page.js "$FILE" 2>&1
    fi
fi
