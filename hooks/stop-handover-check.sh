#!/bin/bash
# stop-handover-check.sh — если сессия substantive и handover не создан,
# пишет pending-маркер для следующей сессии.
# НЕ блокирует закрытие, НЕ форсит Claude. Пассивное напоминание.
#
# Skip-логика:
#   - < 5 substantive tool calls (Edit/Write/NotebookEdit/Bash-write) И < 15 мин = skip
#   - иначе = substantive, проверить handover, если нет → pending
#
# Handover засчитывается если в ~/.claude/handovers/*.md есть session_id в теле/фронтматтере.

set -uo pipefail  # forgiving, не -e

HANDOVERS_DIR="$HOME/.claude/handovers"
PENDING_DIR="$HANDOVERS_DIR/.pending"
SESSIONS_DIR="$HOME/.claude/projects/-Users-antonk"
LOG="$HOME/.claude/logs/stop-handover-check.log"

mkdir -p "$PENDING_DIR" "$(dirname "$LOG")"

ts() { date "+%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

# Последний модифицированный .jsonl = текущая сессия
LATEST=$(ls -t "$SESSIONS_DIR"/*.jsonl 2>/dev/null | head -1)
if [ -z "${LATEST:-}" ] || [ ! -f "$LATEST" ]; then
    log "skip: no session jsonl"
    exit 0
fi

SESSION_ID=$(basename "$LATEST" .jsonl)

# Parse через python3: substantive counts + duration
STATS=$(LATEST="$LATEST" python3 <<'PYEOF' 2>/dev/null
import json, os, re
from datetime import datetime

path = os.environ.get("LATEST")
if not path:
    print("0 0 0")
    raise SystemExit

substantive_tools = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
# Bash считаем substantive только если НЕ read-only команда
read_only_re = re.compile(
    r'^\s*(git\s+(status|log|diff|show|branch|pull|fetch|remote)|'
    r'ls|cat|head|tail|wc|grep\s|find\s|pwd|echo|date|which\s|'
    r'file\s|du\s|df\s|ps\s|top\s|uptime|whoami|hostname|env)\b'
)

substantive = 0
bash_substantive = 0
first_ts = None
last_ts = None

try:
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue

            t = d.get("timestamp")
            if t:
                if not first_ts:
                    first_ts = t
                last_ts = t

            msg = d.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "tool_use":
                    continue
                name = item.get("name", "")
                if name in substantive_tools:
                    substantive += 1
                elif name == "Bash":
                    cmd = (item.get("input") or {}).get("command", "") or ""
                    if not read_only_re.match(cmd):
                        bash_substantive += 1
except Exception:
    pass

def parse(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

f_ts, l_ts = parse(first_ts), parse(last_ts)
duration_min = 0
if f_ts and l_ts:
    duration_min = max(0, int((l_ts - f_ts).total_seconds() / 60))

print(f"{substantive} {bash_substantive} {duration_min}")
PYEOF
)

if [ -z "${STATS:-}" ]; then
    log "skip: stats parse failed for $SESSION_ID"
    exit 0
fi

SUBST=$(echo "$STATS" | awk '{print $1+0}')
BASH_SUBST=$(echo "$STATS" | awk '{print $2+0}')
DURATION=$(echo "$STATS" | awk '{print $3+0}')
TOTAL=$((SUBST + BASH_SUBST))

# Skip: несущественная сессия
IS_SUBST=0
if [ "$TOTAL" -ge 5 ]; then
    IS_SUBST=1
elif [ "$DURATION" -ge 15 ] && [ "$TOTAL" -ge 2 ]; then
    IS_SUBST=1
fi

if [ "$IS_SUBST" -eq 0 ]; then
    log "skip: session $SESSION_ID non-substantive (subst=$TOTAL dur=${DURATION}m)"
    # Cleanup устаревший pending если был
    rm -f "$PENDING_DIR/$SESSION_ID" 2>/dev/null || true
    exit 0
fi

# Есть ли handover с этим session_id?
HAS_HANDOVER=0
if ls "$HANDOVERS_DIR"/*.md >/dev/null 2>&1; then
    if grep -lq "$SESSION_ID" "$HANDOVERS_DIR"/*.md 2>/dev/null; then
        HAS_HANDOVER=1
    fi
fi

if [ "$HAS_HANDOVER" -eq 1 ]; then
    log "ok: session $SESSION_ID has handover (subst=$TOTAL dur=${DURATION}m)"
    rm -f "$PENDING_DIR/$SESSION_ID" 2>/dev/null || true
    exit 0
fi

# Записать pending-маркер
cat > "$PENDING_DIR/$SESSION_ID" <<EOF
session_id=$SESSION_ID
transcript=$LATEST
substantive_calls=$TOTAL
duration_min=$DURATION
detected_at=$(ts)
cwd_hint=${PWD:-unknown}
EOF

log "PENDING: session $SESSION_ID (subst=$TOTAL dur=${DURATION}m)"
exit 0
