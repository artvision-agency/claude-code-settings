#!/bin/bash
set -euo pipefail
# TG Relay: polls Telegram Bot API getUpdates → outputs for Claude Code session
# Called by CronCreate every 30-60s
# Works alongside MCP plugin (fallback for when notifications don't reach session)

BOT_TOKEN="8275689827:AAE_jIN9NJXrfwUcEPe6XBBPFtHfdX6-pek"
OFFSET_FILE="/tmp/tg-relay-offset.txt"
ALLOWED_IDS="161261562 1857522687"

# Read last offset
OFFSET=0
[ -f "$OFFSET_FILE" ] && OFFSET=$(cat "$OFFSET_FILE")

# Poll getUpdates
RESPONSE=$(curl -s --max-time 5 "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=${OFFSET}&timeout=0&limit=10" 2>/dev/null || echo "")
[ -z "$RESPONSE" ] && exit 0

# Check ok
OK=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',False))" 2>/dev/null || echo "False")
[ "$OK" != "True" ] && exit 0

# Process messages
python3 -c "
import json, sys

data = json.loads('''$RESPONSE''')
results = data.get('result', [])
allowed = {$( echo "$ALLOWED_IDS" | sed 's/ /, /g' )}
max_id = $OFFSET

for update in results:
    uid = update.get('update_id', 0)
    if uid >= max_id:
        max_id = uid + 1

    msg = update.get('message', {})
    if not msg:
        continue

    sender_id = str(msg.get('from', {}).get('id', ''))
    if int(sender_id) not in allowed:
        continue

    text = msg.get('text', '')
    if not text or text.startswith('/start'):
        continue

    user = msg.get('from', {}).get('first_name', 'Unknown')
    chat_id = msg.get('chat', {}).get('id', '')

    # Output for Claude Code session (will appear in cron output)
    print(f'📨 TG от {user} (chat:{chat_id}): {text}')

# Save new offset
print(f'OFFSET:{max_id}', file=sys.stderr)
" 2>/tmp/tg-relay-stderr.txt || true

# Update offset
NEW_OFFSET=$(grep "^OFFSET:" /tmp/tg-relay-stderr.txt 2>/dev/null | cut -d: -f2 || echo "")
[ -n "$NEW_OFFSET" ] && [ "$NEW_OFFSET" != "0" ] && echo "$NEW_OFFSET" > "$OFFSET_FILE"
