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

LOG_PATH = "/tmp/factcheck-hook-skip.log"
def log_skip(reason, cmd_preview=""):
    from datetime import datetime as _dt
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{_dt.now().isoformat()}] pre-scp-kp-strict-factcheck SKIP: {reason}\n")
            if cmd_preview:
                f.write(f"  cmd: {cmd_preview[:300]}\n")
    except Exception:
        pass

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw)
    cmd = data.get("tool_input", {}).get("command", "")
except Exception as e:
    log_skip(f"json.loads failed: {e}", raw[:200])
    sys.exit(0)

if not cmd:
    log_skip("empty cmd")
    sys.exit(0)

# Матчим scp по ДВУМ паттернам:
# 1) source path: presales/<slug>/kp/*.html
# 2) destination path: /var/www/artvision/kp/<slug>/
SRC_PAT = r"scp\s+.*presales/[\w-]+/kp/.*\.html"
DST_PAT = r"scp\s+.*/var/www/artvision/kp/[\w-]+/"
src_match = re.search(SRC_PAT, cmd, re.IGNORECASE)
dst_match = re.search(DST_PAT, cmd, re.IGNORECASE)
if not (src_match or dst_match):
    # Не KP-scp, тихо пропускаем
    sys.exit(0)

# Ищем slug — приоритет: source path → destination path
slug_m = re.search(r"presales/([\w-]+)/kp/", cmd) or re.search(r"/var/www/artvision/kp/([\w-]+)/", cmd)
slug = slug_m.group(1) if slug_m else None
if not slug:
    log_skip("KP scp matched but slug not extracted", cmd[:200])
    sys.exit(0)

# Проверяем наличие свежего (< 2 часов) factcheck-отчёта
base = os.path.expanduser(f"~/artvision-data/presales/{slug}")
reports = glob.glob(f"{base}/factcheck-strict-*.md") + glob.glob(f"{base}/factcheck-*.md") + glob.glob(f"{base}/factcheck-{slug}*.md")
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
