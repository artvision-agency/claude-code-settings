#!/usr/bin/env bash
# start.sh — run the voice listener in foreground with proper env
# Stop: Ctrl-C

set -euo pipefail

cd "$(dirname "$0")"

# Export Groq key from tokens.json if not already set
if [[ -z "${GROQ_API_KEY:-}" ]]; then
  GROQ_API_KEY=$(/usr/bin/env python3 -c "
import json
t = json.load(open('/Users/antonk/artvision-data/tokens.json'))
g = t.get('groq')
print(g.get('api_key','') if isinstance(g, dict) else (g or ''))
")
  export GROQ_API_KEY
fi

if [[ -z "$GROQ_API_KEY" ]]; then
  echo "ERROR: GROQ_API_KEY not found in tokens.json" >&2
  exit 1
fi

echo "▶ Voice listener starting. Say 'эй клод' followed by a command."
echo "  Logs: ~/.claude/voice/command.log (commands) + debug.log (everything)"
echo "  Stop: Ctrl-C"
echo ""

exec ./venv/bin/python voice_listener.py
