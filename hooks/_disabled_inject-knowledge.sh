#!/bin/bash
# UserPromptSubmit hook: detects task domain from prompt keywords
# and injects relevant knowledge/<domain>/rules.md into context.
# Karpathy Wiki automation — fixes "rule exists but nobody reads it" problem.
set -euo pipefail

KNOWLEDGE_DIR="$HOME/artvision-data/knowledge"
[ -d "$KNOWLEDGE_DIR" ] || exit 0

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('prompt','').lower())" 2>/dev/null || echo "")
[ -z "$PROMPT" ] && exit 0

MATCHED=()

match() {
  local domain="$1"; shift
  for kw in "$@"; do
    if echo "$PROMPT" | grep -qiE "\b$kw\b|$kw"; then
      MATCHED+=("$domain")
      return
    fi
  done
}

match "seo"            "seo" "сео" "ранжирован" "schema" "robots" "canonical" "tf.?idf" "кластер" "серп" "serp" "позици" "ключев"
match "kp-presale"     "кп\b" "presale" "коммерческ" "предложени" "клиент.*бриф" "онбординг" "pricing" "цена кп"
match "clients"        "клиент" "retention" "upsell" "отношени" "бюджет клиент"
match "cms"            "bitrix" "битрикс" "modx" "wordpress" "вп \|wp "
match "products"       "card duel" "aivision" "artsync" "direct.?radar" "cardwell" "продукт"
match "music"          "suno" "музык" "beat" "sync licensing"
match "infrastructure" "vps" "deploy" "деплой" "cron" "hook" "nginx" "pm2" "launchagent" "ssh"

[ ${#MATCHED[@]} -eq 0 ] && exit 0

UNIQUE_DOMAINS=$(printf "%s\n" "${MATCHED[@]}" | sort -u)

echo ""
echo "📚 Knowledge Wiki — relevant domain rules auto-loaded:"
echo ""

for domain in $UNIQUE_DOMAINS; do
  RULES_FILE="$KNOWLEDGE_DIR/$domain/rules.md"
  HYP_FILE="$KNOWLEDGE_DIR/$domain/hypotheses.md"

  if [ -f "$RULES_FILE" ]; then
    echo "── $domain/rules.md ──"
    cat "$RULES_FILE"
    echo ""
  fi
  if [ -f "$HYP_FILE" ]; then
    HYP_LINES=$(wc -l <"$HYP_FILE" | tr -d ' ')
    if [ "$HYP_LINES" -gt 3 ]; then
      echo "── $domain/hypotheses.md (test when possible) ──"
      cat "$HYP_FILE"
      echo ""
    fi
  fi
done

echo "⚠️  После задачи: обнови knowledge/$domain/knowledge.md или hypotheses.md если появились инсайты."
echo ""

exit 0
