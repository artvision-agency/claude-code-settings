#!/bin/bash
# UserPromptSubmit hook: если есть свежий флаг self-challenge от Stop хука —
# инжектит system-reminder и очищает флаг
# TTL: 15 минут (флаг старше — игнорируем)

set -euo pipefail

FLAG_FILE="/tmp/self-challenge-needed.json"

if [ ! -f "$FLAG_FILE" ]; then
  exit 0
fi

# TTL 15 минут
AGE=$(( $(date +%s) - $(stat -f %m "$FLAG_FILE" 2>/dev/null || stat -c %Y "$FLAG_FILE" 2>/dev/null || echo 0) ))
if [ "$AGE" -gt 900 ]; then
  rm -f "$FLAG_FILE"
  exit 0
fi

# Формируем system-reminder для stdout (UserPromptSubmit: stdout = additional context)
FLAGS_SUMMARY=$(python3 - << PYEOF
import json
try:
    d = json.load(open("$FLAG_FILE"))
    lines = []
    for f in d.get("flags", []):
        matches = ", ".join(str(m) for m in f.get("matches", [])[:3])
        lines.append(f"  • {f['type']} [{f['severity']}]: {matches}")
    print("\n".join(lines))
except Exception as e:
    print("")
PYEOF
)

if [ -z "$FLAGS_SUMMARY" ]; then
  rm -f "$FLAG_FILE"
  exit 0
fi

cat << EOF
[SELF-CHALLENGE REQUIRED]
Твой предыдущий ответ содержал потенциальные галлюцинации (цифры/утверждения без URL-источника):
$FLAGS_SUMMARY

ДЕЙСТВИЕ: перед обработкой текущего запроса пользователя — вызови Skill \`challenge-self\` чтобы субагент-скептик нашёл дыры в предыдущем ответе. Если пользователь уже сам спорит/корректирует — self-challenge не нужен (он уже сделал работу за тебя), просто очисти флаг и работай дальше.
EOF

# Очищаем флаг (уже использован)
rm -f "$FLAG_FILE"

exit 0
