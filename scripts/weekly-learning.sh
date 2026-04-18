#!/bin/bash
set -euo pipefail

# Weekly learning review — runs every Sunday
# Collects week's data and triggers Claude to update memory

REPO="$HOME/artvision-data"
MEMORY="$HOME/.claude/projects/-Users-antonk/memory"
TG_TOKENS="$REPO/tokens.json"
OUTPUT="/tmp/weekly-learning-$(date +%Y-%m-%d).md"

cd "$REPO"

echo "# Weekly Learning Review — $(date '+%Y-%m-%d')" > "$OUTPUT"
echo "" >> "$OUTPUT"

# 1. Meaningful commits this week
echo "## Значимые коммиты недели" >> "$OUTPUT"
git log --oneline --since="7 days ago" --all --no-merges 2>/dev/null | grep -v "auto-sync\|chore:" | head -30 >> "$OUTPUT" || echo "No commits" >> "$OUTPUT"
echo "" >> "$OUTPUT"

# 2. Files changed (categories)
echo "## Категории изменений" >> "$OUTPUT"
echo "- clients: $(git log --since='7 days ago' --all --name-only --pretty=format:'' 2>/dev/null | grep '^clients/' | sort -u | wc -l | tr -d ' ')" >> "$OUTPUT"
echo "- scripts: $(git log --since='7 days ago' --all --name-only --pretty=format:'' 2>/dev/null | grep '^scripts/' | sort -u | wc -l | tr -d ' ')" >> "$OUTPUT"
echo "- products: $(git log --since='7 days ago' --all --name-only --pretty=format:'' 2>/dev/null | grep '^products/' | sort -u | wc -l | tr -d ' ')" >> "$OUTPUT"
echo "- docs: $(git log --since='7 days ago' --all --name-only --pretty=format:'' 2>/dev/null | grep '^docs/' | sort -u | wc -l | tr -d ' ')" >> "$OUTPUT"
echo "" >> "$OUTPUT"

# 3. Memory files last modified
echo "## Memory файлы (последнее обновление)" >> "$OUTPUT"
ls -lt "$MEMORY"/*.md 2>/dev/null | awk '{print $6, $7, $8, $9}' | head -15 >> "$OUTPUT"
echo "" >> "$OUTPUT"

# 4. Open TODOs
echo "## Открытые задачи" >> "$OUTPUT"
for f in "$REPO/TODO.md" "$REPO/presale/TODO.md" "$REPO/products/TODO.md"; do
    if [ -f "$f" ]; then
        echo "### $(basename $(dirname "$f"))/$(basename "$f")" >> "$OUTPUT"
        grep '^\- \[ \]' "$f" 2>/dev/null | head -10 >> "$OUTPUT" || echo "(нет)" >> "$OUTPUT"
        echo "" >> "$OUTPUT"
    fi
done

# 5. Summary prompt for Claude
echo "## Prompt для Claude" >> "$OUTPUT"
cat >> "$OUTPUT" << 'EOF'

Проанализируй эту неделю и обнови:
1. lessons.md — новые уроки (инциденты, паттерны, находки)
2. interaction-patterns.md — как изменилось взаимодействие
3. shortcuts.md — новые ассоциации/команды
4. MEMORY.md — обновить статусы проектов/клиентов
5. Удалить устаревшее из memory файлов
EOF

echo ""
echo "Weekly learning data saved to: $OUTPUT"
echo "Run: claude --prompt 'прочитай $OUTPUT и обнови базу знаний'"

# Wiki maintenance — auto-promote 3/3 hypotheses, flag stale
if [ -x /Users/antonk/artvision-data/scripts/wiki-maintenance.py ]; then
  echo ""
  echo "=== Wiki Maintenance ==="
  python3 /Users/antonk/artvision-data/scripts/wiki-maintenance.py
  cd /Users/antonk/artvision-data || exit 0
  git add knowledge/ 2>/dev/null || true
  if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "wiki: auto-maintenance $(date +%F)" && git push
  fi
fi
