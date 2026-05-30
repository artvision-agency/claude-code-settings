#!/usr/bin/env bash
# pre-scp-medical-aggregator.sh — PreToolUse Bash hook
#
# Блокирует scp клиентских КП медицинского профиля если в clients/<name>/
# нет свежего aggregator-audit-YYYY-MM-DD.json младше 7 дней.
#
# Прецедент: AdvertMed Wave 2 04.05.2026 — 21 КП Казань, в каждом заявлено
# «8 шагов методологии», реально запущено 4. Антон поймал на /sync.
# См. ~/.claude/rules/medical-kp.md секция «Прецедент».
#
# Bypass: AGGREGATOR_AUDIT_SKIP=1
# Лог: ~/.claude/logs/pre-scp-medical-aggregator.log

set -euo pipefail

LOG="$HOME/.claude/logs/pre-scp-medical-aggregator.log"
mkdir -p "$(dirname "$LOG")"

# Read tool input from stdin (Claude Code hook protocol)
INPUT="$(cat || true)"

# Extract command from JSON input
COMMAND="$(echo "$INPUT" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    print("")
' 2>/dev/null || true)"

# Bypass via env
if [[ "${AGGREGATOR_AUDIT_SKIP:-0}" == "1" ]]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] BYPASS via AGGREGATOR_AUDIT_SKIP=1 :: $COMMAND" >> "$LOG"
    echo "$INPUT"
    exit 0
fi

# Only check scp commands targeting clients/*/kp* or kp/<slug> on artvision.pro VPS
if ! echo "$COMMAND" | grep -qE 'scp.*(clients/[^/]+/.*kp.*\.html|kp/[^/]+/.*\.html)'; then
    echo "$INPUT"
    exit 0
fi

# Extract local file path (first non-option arg after scp/-q/-o etc)
LOCAL_PATH="$(echo "$COMMAND" | grep -oE 'clients/[^ ]+\.html' | head -1 || true)"
if [[ -z "$LOCAL_PATH" ]]; then
    echo "$INPUT"
    exit 0
fi

# Extract client slug
CLIENT_SLUG="$(echo "$LOCAL_PATH" | awk -F/ '{print $2}')"
CLIENT_DIR="$HOME/artvision-data/clients/$CLIENT_SLUG"

if [[ ! -d "$CLIENT_DIR" ]]; then
    echo "$INPUT"
    exit 0
fi

# Determine if this is a medical client
# Sources of truth: config.yaml profile field OR design_profile.type=enterprise+medical-kp.md
IS_MEDICAL=0
if [[ -f "$CLIENT_DIR/config.yaml" ]]; then
    IS_MEDICAL="$(python3 -c "
import yaml, sys
try:
    cfg = yaml.safe_load(open('$CLIENT_DIR/config.yaml'))
    profile = (cfg.get('profile') or cfg.get('segment') or '').lower()
    industry = (cfg.get('industry') or '').lower()
    medical_keywords = ['medical', 'медиц', 'клиник', 'стом', 'дент', 'космет', 'флебол', 'репродукт', 'реабил', 'офтальм']
    is_med = any(k in profile or k in industry for k in medical_keywords)
    print('1' if is_med else '0')
except Exception:
    print('0')
" 2>/dev/null || echo "0")"
fi

# Heuristic fallback: filename or path contains medical markers
if [[ "$IS_MEDICAL" == "0" ]]; then
    if echo "$CLIENT_SLUG $LOCAL_PATH" | grep -qiE 'clinic|dental|dent|stom|advertmed|varikoz|медиц|клиник|косметол|флебол'; then
        IS_MEDICAL=1
    fi
fi

if [[ "$IS_MEDICAL" != "1" ]]; then
    echo "$INPUT"
    exit 0
fi

# Check for fresh aggregator-audit-*.json (< 7 days)
LATEST_AUDIT="$(find "$CLIENT_DIR" -maxdepth 3 -name 'aggregator-audit-*.json' -mtime -7 2>/dev/null | head -1)"

if [[ -n "$LATEST_AUDIT" ]]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] PASS :: $CLIENT_SLUG (medical) :: audit=$LATEST_AUDIT" >> "$LOG"
    echo "$INPUT"
    exit 0
fi

# BLOCK
{
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] BLOCK :: $CLIENT_SLUG (medical) :: no fresh aggregator-audit-*.json"
    echo "  command: $COMMAND"
} >> "$LOG"

cat >&2 <<EOF
[hook] BLOCKED: scp медицинского КП без свежего aggregator-audit

Клиент: $CLIENT_SLUG (определён как медицинский)
Путь: $LOCAL_PATH

Не найден aggregator-audit-YYYY-MM-DD.json младше 7 дней в:
  $CLIENT_DIR/

Исправление:
  python3 ~/artvision-data/scripts/medical/aggregator_audit.py \\
    --brand $CLIENT_SLUG \\
    --region <city> \\
    --output $CLIENT_DIR/aggregator-audit-\$(date +%F).json

Прецедент: AdvertMed Wave 2 04.05.2026 — заявлено 8 шагов методологии,
реально запущено 4. Антон поймал на /sync. Это правило: ~/.claude/rules/medical-kp.md.

Bypass (только если уверен):
  AGGREGATOR_AUDIT_SKIP=1 <команда>
EOF

exit 2
