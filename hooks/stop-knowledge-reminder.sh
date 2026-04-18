#!/bin/bash
# Stop hook: reminds to record insights into knowledge/<domain>/
# if the session touched files in a detectable domain.
# Karpathy Wiki lifecycle: observations → hypotheses → rules.
set -euo pipefail

KNOWLEDGE_DIR="$HOME/artvision-data/knowledge"
[ -d "$KNOWLEDGE_DIR" ] || exit 0

# Input: Stop hook receives session metadata via stdin (JSON)
INPUT=$(cat)

# Extract session transcript path to detect which files were touched
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('transcript_path',''))" 2>/dev/null || echo "")
[ -z "$TRANSCRIPT" ] && exit 0
[ -f "$TRANSCRIPT" ] || exit 0

# Look at last ~50 tool uses for file paths / keywords
RECENT=$(tail -200 "$TRANSCRIPT" 2>/dev/null || echo "")
[ -z "$RECENT" ] && exit 0

DOMAINS=""

add_domain() {
  case "$DOMAINS" in
    *"$1"*) ;;
    *) DOMAINS="$DOMAINS $1" ;;
  esac
}

# Match file paths + keywords
echo "$RECENT" | grep -qiE "seo/|serp|wordstat|topvisor|schema|robots\.txt|canonical" && add_domain "seo"
echo "$RECENT" | grep -qiE "clients/[a-z].*presale|kp/|коммерческое|commercial" && add_domain "kp-presale"
echo "$RECENT" | grep -qiE "bitrix|modx|wordpress|/wp-content" && add_domain "cms"
echo "$RECENT" | grep -qiE "cardwell|aivision|direct-radar|products/" && add_domain "products"
echo "$RECENT" | grep -qiE "suno|music|track|beat" && add_domain "music"
echo "$RECENT" | grep -qiE "pm2|nginx|launchagent|cron|deploy\.sh|vps" && add_domain "infrastructure"
echo "$RECENT" | grep -qiE "clients/[a-z]" && add_domain "clients"

[ -z "$DOMAINS" ] && exit 0

# Additional signal: only nag if at least 3 Edit/Write events happened
EDITS=$(echo "$RECENT" | grep -cE '"name":\s*"(Edit|Write)"' || echo 0)
[ "$EDITS" -lt 3 ] && exit 0

echo ""
echo "📚 Knowledge Wiki reminder — значимая работа в доменах:$DOMAINS"
echo ""
for domain in $DOMAINS; do
  DIR="$KNOWLEDGE_DIR/$domain"
  [ -d "$DIR" ] || continue
  echo "  • $domain/ — обнови knowledge.md (факты) или hypotheses.md (наблюдения)"
done
echo ""
echo "  Lifecycle: observation → hypotheses.md → (3× confirmed) → rules.md"
echo ""

exit 0
