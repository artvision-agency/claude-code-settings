#!/bin/bash
# PostToolUse (Bash): auto-validate after generate_page.py runs
# Triggered by settings.json PostToolUse matcher for Bash

COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

# Only trigger on generate_page.py commands
if ! echo "$COMMAND" | grep -q "generate_page.py"; then
  exit 0
fi

# Find the templates directory
TEMPLATES_DIR=""
if echo "$COMMAND" | grep -q "ant-partners"; then
  TEMPLATES_DIR="/Users/antonk/artvision-data/clients/ant-partners/templates"
elif [ -f "validate_pages.py" ]; then
  TEMPLATES_DIR="$(pwd)"
elif [ -f "../validate_pages.py" ]; then
  TEMPLATES_DIR="$(cd .. && pwd)"
fi

if [ -z "$TEMPLATES_DIR" ] || [ ! -f "$TEMPLATES_DIR/validate_pages.py" ]; then
  exit 0
fi

echo "[hook] Auto-validating after page generation..."
RESULT=$(python3 "$TEMPLATES_DIR/validate_pages.py" 2>&1 | tail -5)

if echo "$RESULT" | grep -q "ALL CHECKS PASSED"; then
  echo "[hook] ✓ Validation: ALL CHECKS PASSED"
else
  echo "[hook] ✗ Validation FAILED — check output above"
  echo "$RESULT"
fi
