#!/bin/bash
# PreToolUse (Bash): перед git push показать summary пуша
# Предотвращает случайный пуш незавершённой работы

COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

# Срабатываем только на git push
if ! echo "$COMMAND" | grep -qE "git\s+push"; then
  exit 0
fi

cd /Users/antonk/artvision-data 2>/dev/null || exit 0

# Показываем что будет запушено
echo "--- Git Push Summary ---"

# Последние коммиты которые уйдут на remote
UNPUSHED=$(git log --oneline origin/main..HEAD 2>/dev/null | head -10)
if [ -n "$UNPUSHED" ]; then
  COUNT=$(echo "$UNPUSHED" | wc -l | tr -d ' ')
  echo "Коммитов к отправке: $COUNT"
  echo "$UNPUSHED"
else
  echo "Нет новых коммитов для push."
fi

# Какие клиенты затронуты
CLIENTS=$(git diff --name-only origin/main..HEAD 2>/dev/null | grep "^clients/" | sed 's|clients/||' | cut -d'/' -f1 | sort -u)
if [ -n "$CLIENTS" ]; then
  echo ""
  echo "Затронутые клиенты: $CLIENTS"
fi

# HTML с внешними URL
HTML_FILES=$(git diff --name-only origin/main..HEAD 2>/dev/null | grep "\.html$")
if [ -n "$HTML_FILES" ]; then
  PROBLEM_HTML=""
  while IFS= read -r f; do
    if [ -f "$f" ]; then
      EXT=$(grep -oE 'https?://[^"'\''> ]+' "$f" 2>/dev/null | grep -v 'habr.com\|artvision\|mailto:\|tel:' | wc -l | tr -d ' ')
      if [ "$EXT" -gt 0 ]; then
        PROBLEM_HTML="${PROBLEM_HTML}  $f ($EXT внешних URL)\n"
      fi
    fi
  done <<< "$HTML_FILES"
  if [ -n "$PROBLEM_HTML" ]; then
    echo ""
    echo "HTML с внешними URL:"
    echo -e "$PROBLEM_HTML"
  fi
fi

echo "------------------------"

# FACTCHECK: проверить HTML клиентов/продуктов перед пушем
FACTCHECK_SCRIPT="/Users/antonk/artvision-data/scripts/factcheck-html.py"
if [ -f "$FACTCHECK_SCRIPT" ] && [ -n "$HTML_FILES" ]; then
  CLIENT_HTML=""
  while IFS= read -r f; do
    if [ -f "$f" ] && echo "$f" | grep -qE "^(clients|products|presales)/"; then
      CLIENT_HTML="${CLIENT_HTML} $f"
    fi
  done <<< "$HTML_FILES"

  if [ -n "$CLIENT_HTML" ]; then
    echo ""
    echo "--- FACTCHECK ---"
    FACTCHECK_FAIL=0
    for hf in $CLIENT_HTML; do
      python3 "$FACTCHECK_SCRIPT" "$hf" 2>/dev/null
      if [ $? -ne 0 ]; then
        FACTCHECK_FAIL=1
      fi
    done
    if [ "$FACTCHECK_FAIL" -eq 1 ]; then
      echo ""
      echo "⚠️  FACTCHECK: есть CRITICAL issues в HTML. Проверьте перед пушем."
    fi
    echo "-----------------"
  fi
fi

exit 0
