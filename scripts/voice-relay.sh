#!/bin/bash
set -euo pipefail
# Voice Relay: VPS voice_inbox.jsonl → Claude Code session
# Usage: called by Claude Code cron every 30s-1min

PROCESSED="/Users/antonk/.claude_temp_scripts/voice_processed.txt"
VPS="root@80.90.181.152"

# Pull new entries from VPS
NEW=$(ssh -o ConnectTimeout=5 "$VPS" "cat /root/voice_inbox.jsonl 2>/dev/null" 2>/dev/null || echo "")

if [ -z "$NEW" ]; then
    exit 0
fi

# Check what we already processed
mkdir -p "$(dirname "$PROCESSED")"
touch "$PROCESSED"

# Use process substitution instead of pipe to avoid subshell stdout loss
while IFS= read -r line; do
    [ -z "$line" ] && continue

    # Extract msg_id as unique key
    MSG_ID=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('msg_id',''))" 2>/dev/null || echo "")
    [ -z "$MSG_ID" ] && continue

    # Skip if already processed
    grep -q "^${MSG_ID}$" "$PROCESSED" 2>/dev/null && continue

    # Extract text
    TEXT=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('text',''))" 2>/dev/null || echo "")
    [ -z "$TEXT" ] && continue

    # Mark as processed
    echo "$MSG_ID" >> "$PROCESSED"

    # Output the voice command (picked up by cron)
    echo "🎤 VOICE: $TEXT"
done <<< "$NEW"
