#!/bin/bash
# tg-send-tracked.sh — отправляет сообщение в TG + регистрирует ожидаемые ответы в трекере.
# Listener потом матчит входящие ответы и обновляет статусы.
#
# Usage:
#   tg-send-tracked.sh <channel> <recipient> "сообщение" --questions "q1||q2||q3"
#
# Пример:
#   tg-send-tracked.sh team andrey "@PandaCaffe утро — статус" \
#     --questions "Avto.world прогон 14.04||Geely A2Auto||Extru март отчёт||Avto.world статьи||60 доноров||Проливы 5К/нед"
#
# channel:   team | anton | <chat_id>
# recipient: andrey | anton | stas | <name>  (кто должен ответить)
# questions: "q1||q2||q3..." — список вопросов через ||

set -euo pipefail

CHANNEL="${1:?channel required (team|anton|chat_id)}"
RECIPIENT="${2:?recipient required}"
MSG="${3:?message required}"
shift 3

QUESTIONS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --questions)
            QUESTIONS="$2"; shift 2 ;;
        *)
            echo "Unknown flag: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$QUESTIONS" ]; then
    echo "ERROR: --questions required (use || as separator)" >&2
    exit 1
fi

# Отправляем через стандартный tg-send.sh → получаем msg_id
RESPONSE="$("$(dirname "$0")/tg-send.sh" "$CHANNEL" "$MSG")" || {
    echo "$RESPONSE" >&2
    exit 1
}

MSG_ID="$(printf '%s' "$RESPONSE" | grep -oE '"message_id":[0-9]+' | head -1 | cut -d: -f2)"
CHAT_ID="$(printf '%s' "$RESPONSE" | grep -oE '"chat":\{"id":-?[0-9]+' | head -1 | grep -oE '\-?[0-9]+$')"

if [ -z "${MSG_ID:-}" ] || [ -z "${CHAT_ID:-}" ]; then
    echo "ERROR: could not extract msg_id/chat_id from response" >&2
    exit 1
fi

# Регистрируем в трекере
REQ_ID="req_$(date -u +%Y%m%d_%H%M%S)_${RECIPIENT}"
TRACKER="$HOME/artvision-data/sync/tg-tracking/status_requests.jsonl"
mkdir -p "$(dirname "$TRACKER")"

python3 - <<PYEOF
import json
from datetime import datetime, timezone

questions = """$QUESTIONS""".split("||")
record = {
    "id": "$REQ_ID",
    "chat_id": int("$CHAT_ID"),
    "msg_id": int("$MSG_ID"),
    "recipient": "$RECIPIENT",
    "sent_at": datetime.now(timezone.utc).isoformat(),
    "status": "awaiting",
    "clarify_count": 0,
    "questions": [
        {"n": i+1, "text": q.strip(), "status": "pending", "answer": None}
        for i, q in enumerate(questions) if q.strip()
    ]
}
with open("$TRACKER", "a") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
print(f"📋 Tracked: $REQ_ID — msg_id=$MSG_ID, {len(record['questions'])} questions")
PYEOF
