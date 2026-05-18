#!/bin/bash
# pre-stop-done-verify.sh — блокирует Stop если «готово» для КП без verification
# Прецедент: сессия adc5590f (15-17.05.2026) — 6+ раз «готово» без проверки
# Bypass: DONE_VERIFY_SKIP=1
set -euo pipefail
[[ "${DONE_VERIFY_SKIP:-}" == "1" ]] && exit 0

INPUT=$(cat 2>/dev/null || true)
[[ -z "$INPUT" ]] && exit 0

TMPPY=$(mktemp /tmp/done_verify_XXXXXX)
cat > "$TMPPY" << 'PYEOF'
import sys, json, re

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw)
    messages = data.get("messages", [])
except Exception:
    sys.exit(0)

if len(messages) < 3:
    sys.exit(0)

transcript = json.dumps(messages, ensure_ascii=False)
recent = json.dumps(messages[-8:], ensure_ascii=False)

kp_patterns = [
    r"presales/[\w-]+/kp/",
    r"preview/[\w-]+/kp/",
    r"artvision\.pro/[\w-]+/kp/",
    r"scp.*presales.*html",
]
has_kp = any(re.search(p, transcript, re.IGNORECASE) for p in kp_patterns)
if not has_kp:
    sys.exit(0)

done_patterns = [
    r"готов[аоы]?\s+(к|для|к отправке)",
    r"можно\s+отправлять",
    r"всё\s+готово",
    r"деплой\s+финал",
    r"16/16.*OK",
]
has_done = any(re.search(p, recent, re.IGNORECASE) for p in done_patterns)
if not has_done:
    sys.exit(0)

verify_patterns = [
    r"playwright|test_kp\.py",
    r"\d+/\d+\s*(OK|PASS)",
    r"CRITICAL.*0|0.*CRITICAL",
    r"v4-(desktop|mobile|tablet).*png",
    r"BLOCK.*PASS|CONDITIONAL.*PASS",
]
last30 = json.dumps(messages[-30:], ensure_ascii=False)
has_verify = any(re.search(p, last30, re.IGNORECASE) for p in verify_patterns)

if not has_verify:
    print("⚠️  pre-stop-done-verify: «готово» для КП без verification:", file=sys.stderr)
    print("   Нужно одно из:", file=sys.stderr)
    print("   — Read screenshot (v4-desktop/mobile.png)", file=sys.stderr)
    print("   — Playwright output: N/N OK", file=sys.stderr)
    print("   — factcheck: PASS / 0 CRITICAL", file=sys.stderr)
    print("   Bypass: DONE_VERIFY_SKIP=1", file=sys.stderr)
    sys.exit(2)
PYEOF

python3 "$TMPPY" "$INPUT"
STATUS=$?
rm -f "$TMPPY"
exit $STATUS
