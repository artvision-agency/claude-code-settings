#!/bin/bash
# pre-scp-kp-strict-factcheck.sh — блокирует scp клиентского КП без strict-factcheck
# Прецедент: сессия adc5590f — 4 CRITICAL (Wink/0.62/Amazon EU) найдены ПОСЛЕ деплоя
# Bypass: FACTCHECK_STRICT_SKIP=1
set -euo pipefail
[[ "${FACTCHECK_STRICT_SKIP:-}" == "1" ]] && exit 0

INPUT=$(cat 2>/dev/null || true)
[[ -z "$INPUT" ]] && exit 0

TMPPY=$(mktemp /tmp/kp_factcheck_XXXXXX)
cat > "$TMPPY" << 'PYEOF'
import sys, json, re, os, glob
from datetime import datetime, timedelta

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw)
    cmd = data.get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)

if not cmd:
    sys.exit(0)

# Матчим scp на presales/*/kp/*.html
kp_scp = bool(re.search(
    r"scp\s+.*presales/[\w-]+/kp/.*\.html|scp\s+.*presales/[\w-]+/kp/index\.html",
    cmd, re.IGNORECASE
))
if not kp_scp:
    sys.exit(0)

# Ищем slug из пути
slug_m = re.search(r"presales/([\w-]+)/kp/", cmd)
slug = slug_m.group(1) if slug_m else None

# Проверяем наличие свежего (< 2 часов) factcheck-отчёта
if slug:
    base = os.path.expanduser(f"~/artvision-data/presales/{slug}")
    reports = glob.glob(f"{base}/factcheck-strict-*.md") + glob.glob(f"{base}/factcheck-*.md")
    cutoff = datetime.now() - timedelta(hours=2)
    fresh = [r for r in reports if datetime.fromtimestamp(os.path.getmtime(r)) > cutoff]
    if fresh:
        sys.exit(0)

print("⛔ pre-scp-kp-strict-factcheck: нет свежего factcheck-отчёта для KP!", file=sys.stderr)
if slug:
    print(f"   КП: {slug}", file=sys.stderr)
print("", file=sys.stderr)
print("   Запусти ПЕРЕД деплоем:", file=sys.stderr)
print("   strict-factchecker agent ИЛИ", file=sys.stderr)
print(f"   python3 ~/artvision-data/scripts/factcheck-v2.py --strict ~/artvision-data/presales/{slug or 'SLUG'}/kp/index.html", file=sys.stderr)
print("", file=sys.stderr)
print("   Bypass: FACTCHECK_STRICT_SKIP=1", file=sys.stderr)
sys.exit(1)
PYEOF

python3 "$TMPPY" "$INPUT"
STATUS=$?
rm -f "$TMPPY"
exit $STATUS
