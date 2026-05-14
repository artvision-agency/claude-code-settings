#!/usr/bin/env bash
# stop-deploy-url-check.sh — проверяет что deploy-ответ начинается с URL.
# Правило: ~/.claude/projects/-Users-antonk/memory/feedback_deploy_url_first.md
# Триггеры в последнем assistant message: "Live URL:", "scp ... :/var/www/",
# "Опубликовано", "https://artvision.pro/(kp|preview)/"
# Если URL найден но НЕ в первых 3 строках → exit 2 с напоминанием.
# Bypass: DEPLOY_URL_OK=1

[[ "${DEPLOY_URL_OK:-}" == "1" ]] && exit 0

# Stop hook input — JSON со stdin: {session_id, stop_hook_active, ...}
INPUT=$(cat 2>/dev/null || echo '{}')

# Найти последний transcript .jsonl и взять последний assistant message
SESSION_ID=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

JSONL="$HOME/.claude/projects/-Users-antonk/$SESSION_ID.jsonl"
[[ ! -f "$JSONL" ]] && exit 0

LAST_TEXT=$(python3 - "$JSONL" <<'PY'
import json, sys
path = sys.argv[1]
last = ""
with open(path, encoding='utf-8') as f:
    for line in f:
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") != "assistant":
            continue
        msg = ev.get("message", {})
        content = msg.get("content", [])
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    last = c.get("text", "")
        elif isinstance(content, str):
            last = content
print(last)
PY
)

[[ -z "$LAST_TEXT" ]] && exit 0

# Deploy маркеры
if ! echo "$LAST_TEXT" | grep -qE "(Live URL:|scp .* :/var/www/|Опубликовано|https://artvision\.pro/(kp|preview|orm))"; then
    exit 0
fi

# Извлечь URL artvision.pro
URL=$(echo "$LAST_TEXT" | grep -oE "https://artvision\.pro/[a-zA-Z0-9/_.-]+" | head -1)
[[ -z "$URL" ]] && exit 0

# Проверить присутствует ли URL в первых 3 строках
FIRST3=$(echo "$LAST_TEXT" | head -3)
if echo "$FIRST3" | grep -qF "$URL"; then
    exit 0
fi

cat >&2 <<EOF
⛔ deploy-url-check: URL не в первых 3 строках ответа

Правило: feedback_deploy_url_first.md
Антон смотрит только URL — он должен быть первой строкой.

Найденный URL: $URL

Перепиши ответ начиная с URL.

Bypass: DEPLOY_URL_OK=1 (если осознанно)
EOF
exit 2
