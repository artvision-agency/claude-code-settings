#!/usr/bin/env bash
# qa-kislovodsk.sh — verify-gate монитора безопасности Кисловодска (КМВ).
# Проверяет: синтаксис .py + lint плистов + регрессионные тесты + регистрацию
# в launchd. Любой провал → exit≠0 (для использования как гейт перед «готово»).
set -euo pipefail

PY="${KISLO_PY:-/Library/Frameworks/Python.framework/Versions/3.14/bin/python3}"
[ -x "$PY" ] || PY="$(command -v python3)"

SCRIPTS="$HOME/.claude/scripts"
COMMON="$SCRIPTS/kislovodsk_common.py"
DIGEST="$SCRIPTS/kislovodsk-safety-digest.py"
ALERT="$SCRIPTS/kislovodsk-realtime-alert.py"
HEALTH="$SCRIPTS/kislovodsk-healthcheck.py"
CONFIG="$SCRIPTS/kislovodsk-config.json"
TESTS="$SCRIPTS/tests/test_kislovodsk_monitor.py"

fail=0
pass() { printf '  PASS  %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }
warn() { printf '  WARN  %s\n' "$1"; }   # не валит гейт (N/A на Mac / VPS-cron)

echo "== QA Kislovodsk monitor (PY=$PY) =="

echo "[1] py_compile"
if "$PY" -m py_compile "$COMMON" 2>/dev/null; then pass "compile common"; else bad "compile common"; fi
if "$PY" -m py_compile "$DIGEST" 2>/dev/null; then pass "compile digest"; else bad "compile digest"; fi
if "$PY" -m py_compile "$ALERT"  2>/dev/null; then pass "compile alert";  else bad "compile alert";  fi
if "$PY" -m py_compile "$HEALTH" 2>/dev/null; then pass "compile healthcheck"; else bad "compile healthcheck"; fi

echo "[2] config JSON валиден + секции"
if "$PY" -c "import json,sys; c=json.load(open('$CONFIG')); sys.exit(0 if all(k in c for k in ('keywords','coords','thresholds','channels')) else 1)" 2>/dev/null; then
    pass "kislovodsk-config.json (keywords/coords/thresholds/channels)"
else
    bad "kislovodsk-config.json невалиден / нет секций"
fi

echo "[3] pytest регрессионные тесты"
if "$PY" -m pytest "$TESTS" -q >/tmp/qa-kislovodsk-pytest.log 2>&1; then
    pass "pytest ($(grep -oE '[0-9]+ passed' /tmp/qa-kislovodsk-pytest.log | head -1))"
else
    bad "pytest (см. /tmp/qa-kislovodsk-pytest.log)"
    tail -15 /tmp/qa-kislovodsk-pytest.log | sed 's/^/      /'
fi

echo "[4] launchctl/cron регистрация (боевой = VPS cron; на Mac N/A = WARN)"
LIST="$(launchctl list 2>/dev/null || true)"
if echo "$LIST" | grep -q 'pro.artvision.kislovodsk-safety'; then pass "launchd safety (Mac)"; else warn "launchd safety не загружен (ожидаемо: боевой на VPS cron)"; fi
if echo "$LIST" | grep -q 'pro.artvision.kislovodsk-alert';  then pass "launchd alert (Mac)";  else warn "launchd alert не загружен (ожидаемо: боевой на VPS cron)"; fi

echo
if [ "$fail" -eq 0 ]; then
    echo "== RESULT: PASS =="
    exit 0
else
    echo "== RESULT: FAIL =="
    exit 1
fi
