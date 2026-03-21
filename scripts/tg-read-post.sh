#!/bin/bash
set -euo pipefail
# Читает пост из публичного TG канала по ссылке
# Использование: tg-read-post.sh https://t.me/channel/123
# Или: tg-read-post.sh channel 123

URL="${1:-}"

if [[ "$URL" == https://t.me/* ]]; then
    # Parse URL: https://t.me/channel/123
    CHANNEL=$(echo "$URL" | sed 's|https://t.me/||' | cut -d'/' -f1)
    MSG_ID=$(echo "$URL" | sed 's|https://t.me/||' | cut -d'/' -f2)
elif [[ -n "${2:-}" ]]; then
    CHANNEL="$1"
    MSG_ID="$2"
else
    echo "Usage: tg-read-post.sh https://t.me/channel/123"
    echo "   or: tg-read-post.sh channel 123"
    exit 1
fi

# t.me/s/ = server-rendered preview (no JS needed, no auth)
python3 - "$CHANNEL" "$MSG_ID" << 'PYEOF'
import requests, re, sys

channel = sys.argv[1]
msg_id = sys.argv[2]

url = f"https://t.me/s/{channel}/{msg_id}"
r = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})

if r.status_code != 200:
    print(f"HTTP {r.status_code}", file=sys.stderr)
    sys.exit(1)

# Find the specific post by data-post attribute
pattern = f'data-post="{channel}/{msg_id}"'
start = r.text.find(pattern)
if start < 0:
    print(f"Post {channel}/{msg_id} not found in page", file=sys.stderr)
    sys.exit(1)

# Find message text div
msg_start = r.text.find('tgme_widget_message_text', start)
if msg_start < 0:
    print(f"No text content in post", file=sys.stderr)
    sys.exit(1)

# Extract content
content_start = r.text.find('>', msg_start) + 1
# Walk HTML to find matching closing div
depth = 1
pos = content_start
text = r.text
while depth > 0 and pos < len(text) - 6:
    if text[pos:pos+4] == '<div':
        depth += 1
    elif text[pos:pos+6] == '</div>':
        if depth == 1:
            break
        depth -= 1
    pos += 1

content = text[content_start:pos]
# Clean HTML
clean = re.sub(r'<br\s*/?>', '\n', content)
clean = re.sub(r'<[^>]+>', '', clean)
clean = clean.strip()

if clean:
    print(clean)
else:
    print("Empty post", file=sys.stderr)
    sys.exit(1)
PYEOF
