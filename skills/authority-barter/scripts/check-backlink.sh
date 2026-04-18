#!/usr/bin/env bash
# Проверка статуса backlink после публикации
# Usage: check-backlink.sh <published_url> <client_domain>
# Пример: check-backlink.sh https://apej.ru/2026/05/article intelsteel.ru

set -euo pipefail

URL="${1:-}"
CLIENT_DOMAIN="${2:-}"

if [[ -z "$URL" || -z "$CLIENT_DOMAIN" ]]; then
  echo "Usage: $0 <published_url> <client_domain>"
  echo "Example: $0 https://apej.ru/2026/05/article intelsteel.ru"
  exit 1
fi

echo "=== Authority-Barter: Backlink Check ==="
echo "URL: $URL"
echo "Client: $CLIENT_DOMAIN"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

# 1. HTTP status
echo "--- 1. HTTP status ---"
STATUS=$(curl -sI -o /dev/null -w "%{http_code}" --max-time 15 "$URL" || echo "000")
echo "Status: $STATUS"
if [[ "$STATUS" != "200" ]]; then
  echo "⚠️  URL not 200 — may be removed or moved"
fi
echo

# 2. Page exists — fetch HTML
echo "--- 2. Fetch HTML ---"
HTML_FILE="$(mktemp /tmp/backlink-check.XXXXXX.html)"
trap "rm -f $HTML_FILE" EXIT
if ! curl -sL --max-time 30 "$URL" -o "$HTML_FILE"; then
  echo "❌ Failed to fetch"
  exit 2
fi
echo "Fetched: $(wc -c < "$HTML_FILE") bytes"
echo

# 3. Check for client domain mention
echo "--- 3. Client domain mention ---"
MENTIONS=$(grep -oE "$CLIENT_DOMAIN" "$HTML_FILE" | wc -l | tr -d ' ')
echo "Mentions of $CLIENT_DOMAIN: $MENTIONS"
if [[ "$MENTIONS" == "0" ]]; then
  echo "❌ NO mentions — publication may not contain backlink"
else
  echo "✅ Found"
fi
echo

# 4. Check for href link to client domain
echo "--- 4. Href link ---"
LINKS=$(grep -oE "href=[\"'][^\"']*$CLIENT_DOMAIN[^\"']*[\"']" "$HTML_FILE" | head -5 || true)
if [[ -z "$LINKS" ]]; then
  echo "⚠️  No <a href> links to client domain (only text mention?)"
else
  echo "Found links:"
  echo "$LINKS"
fi
echo

# 5. Check rel attribute
echo "--- 5. Rel attribute check ---"
REL_NOFOLLOW=$(grep -cE 'rel=[\"'\''][^\"'\'']*nofollow' "$HTML_FILE" || echo "0")
REL_SPONSORED=$(grep -cE 'rel=[\"'\''][^\"'\'']*sponsored' "$HTML_FILE" || echo "0")
REL_UGC=$(grep -cE 'rel=[\"'\''][^\"'\'']*ugc' "$HTML_FILE" || echo "0")
echo "nofollow rels on page: $REL_NOFOLLOW"
echo "sponsored rels on page: $REL_SPONSORED"
echo "ugc rels on page: $REL_UGC"
echo "(общая статистика страницы; специфический rel к клиенту нужно проверять руками)"
echo

# 6. Indexation check (Google + Yandex)
echo "--- 6. Indexation check ---"
echo "Google: https://www.google.com/search?q=site:$URL"
echo "Yandex: https://yandex.ru/search/?text=url%3A$URL"
echo "(открыть вручную или через API позже)"
echo

# 7. Write to log
LOG_FILE="$HOME/.claude/skills/authority-barter/logs/backlinks.jsonl"
mkdir -p "$(dirname "$LOG_FILE")"
printf '{"date":"%s","url":"%s","client":"%s","status":"%s","mentions":%s,"has_link":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  "$URL" \
  "$CLIENT_DOMAIN" \
  "$STATUS" \
  "$MENTIONS" \
  "$([ -n "$LINKS" ] && echo "true" || echo "false")" \
  >> "$LOG_FILE"

echo "--- Log ---"
echo "Appended to $LOG_FILE"
echo
echo "=== Done ==="
