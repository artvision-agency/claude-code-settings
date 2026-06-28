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
TESTS="$SCRIPTS/tests/test_kislovodsk_monitor.py"
PLIST_SAFETY="$HOME/Library/LaunchAgents/pro.artvision.kislovodsk-safety.plist"
PLIST_ALERT="$HOME/Library/LaunchAgents/pro.artvision.kislovodsk-alert.plist"

fail=0
pass() { printf '  PASS  %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }

echo "== QA Kislovodsk monitor (PY=$PY) =="

echo "[1] py_compile"
if "$PY" -m py_compile "$COMMON" 2>/dev/null; then pass "compile common"; else bad "compile common"; fi
if "$PY" -m py_compile "$DIGEST" 2>/dev/null; then pass "compile digest"; else bad "compile digest"; fi
if "$PY" -m py_compile "$ALERT"  2>/dev/null; then pass "compile alert";  else bad "compile alert";  fi

echo "[2] plutil -lint плистов"
if plutil -lint "$PLIST_SAFETY" >/dev/null 2>&1; then pass "lint plist safety"; else bad "lint plist safety"; fi
if plutil -lint "$PLIST_ALERT"  >/dev/null 2>&1; then pass "lint plist alert";  else bad "lint plist alert";  fi

echo "[3] pytest регрессионные тесты"
if "$PY" -m pytest "$TESTS" -q >/tmp/qa-kislovodsk-pytest.log 2>&1; then
    pass "pytest ($(grep -oE '[0-9]+ passed' /tmp/qa-kislovodsk-pytest.log | head -1))"
else
    bad "pytest (см. /tmp/qa-kislovodsk-pytest.log)"
    tail -15 /tmp/qa-kislovodsk-pytest.log | sed 's/^/      /'
fi

echo "[4] launchctl регистрация"
LIST="$(launchctl list 2>/dev/null || true)"
if echo "$LIST" | grep -q 'pro.artvision.kislovodsk-safety'; then pass "registered safety (08:30)"; else bad "NOT registered safety"; fi
if echo "$LIST" | grep -q 'pro.artvision.kislovodsk-alert';  then pass "registered alert (30m)";   else bad "NOT registered alert";  fi

echo
if [ "$fail" -eq 0 ]; then
    echo "== RESULT: PASS =="
    exit 0
else
    echo "== RESULT: FAIL =="
    exit 1
fi
