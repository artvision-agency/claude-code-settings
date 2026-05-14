#!/bin/bash
# PostToolUse(Edit|Write): детект "h-tree" / ASCII-tree / таблиц иерархии в client HTML.
# Триггер: clients/*/plan/*.html | clients/*/presale/*.html | clients/*/reports/*.html
# Действие: предупреждение в stderr с пометкой документа для проверки.
# Не блокирует (warn-only).

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

[ -z "$FILE" ] && exit 0

# Только HTML в client-папках
if ! echo "$FILE" | grep -qE 'clients/[^/]+/(plan|presale|reports|kp)/.+\.html$'; then
  exit 0
fi
[ ! -f "$FILE" ] && exit 0

VIOLATIONS=0
DETAILS=""

# Pattern 1: h-tree блок с цветным span
if grep -qE 'class="h-tree"' "$FILE" 2>/dev/null; then
  N=$(grep -c '<span class="h[123456]"' "$FILE" 2>/dev/null || echo 0)
  if [ "$N" -gt 0 ]; then
    VIOLATIONS=$((VIOLATIONS+1))
    DETAILS+="• h-tree блок с цветным span — найдено $N span'ов (H1-H6). Переделай в <ul>/<ol>.\n"
  fi
fi

# Pattern 2: ASCII-tree символы в HTML
if grep -qE '├──|│   ├|└──' "$FILE" 2>/dev/null; then
  VIOLATIONS=$((VIOLATIONS+1))
  DETAILS+="• ASCII-tree символы (├── / │   / └──) в HTML — не работают в браузере как иерархия. Переделай в <ul>/<ol>.\n"
fi

# Pattern 3: таблица с колонкой "уровень" / "H1/H2/H3"
if grep -qiE '<th[^>]*>[^<]*уровень[^<]*</th>|<th[^>]*>H[123][^<]*</th>' "$FILE" 2>/dev/null; then
  VIOLATIONS=$((VIOLATIONS+1))
  DETAILS+="• Таблица с колонкой 'уровень' или 'H1/H2/H3' — иерархия должна быть <ul>/<ol>, не таблица.\n"
fi

if [ "$VIOLATIONS" -gt 0 ]; then
  cat <<EOF >&2

⚠️  post-edit-list-check: $FILE
   Нарушение правила document-list-format.md ($VIOLATIONS):
$(echo -e "$DETAILS")
   Правило: ~/.claude/rules/document-list-format.md
   Memory: ~/.claude/projects/-Users-antonk/memory/feedback_lists_not_trees_for_structures.md
   Прецедент: Антон 13.05 — «постоянно прошу списками».

EOF
fi

exit 0
