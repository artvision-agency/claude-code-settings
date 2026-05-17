#!/usr/bin/env bash
# Tests for pre-deploy-delivery-date-source.py
# Calls hook directly (bypasses Claude harness)
set -uo pipefail

HOOK_PY="$HOME/.claude/hooks/pre-deploy-delivery-date-source.py"
PASS=0
FAIL=0
TMPDIR_LOCAL=$(mktemp -d)

cleanup() { rm -rf -- "$TMPDIR_LOCAL"; }
trap cleanup EXIT

ok() { echo "  [PASS] $1"; PASS=$(( PASS + 1 )); }
fail() { echo "  [FAIL] $1"; FAIL=$(( FAIL + 1 )); }

run_hook() {
  local payload="$1"
  local exit_code=0
  python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || exit_code=$?
  echo $exit_code
}

echo "=== pre-deploy-delivery-date-source.py ==="

# -----------------------------------------------------------------------
# TEST 1: HAPPY PATH — HTML with no delivery dates → exit 0
# -----------------------------------------------------------------------
html_no_dates="$TMPDIR_LOCAL/no-dates.html"
cat > "$html_no_dates" <<'EOF'
<!DOCTYPE html><html><body>
<h1>ЖК Ромашка</h1>
<p>Квартиры от 5 млн рублей. Звоните!</p>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_no_dates")
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 1: No delivery dates → exit 0"
else
  fail "TEST 1: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 2: Non-scp command → hook ignores → exit 0
# -----------------------------------------------------------------------
html_with_date="$TMPDIR_LOCAL/with-date.html"
cat > "$html_with_date" <<'EOF'
<!DOCTYPE html><html><body>
<p>Срок сдачи: Q2 2026 <a href="https://setlgroup.ru/complex/riviera">setlgroup.ru</a></p>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}')
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 2: Non-scp command → hook skips → exit 0"
else
  fail "TEST 2: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 3: BYPASS — DELIVERY_DATE_SKIP=1 → exit 0
# -----------------------------------------------------------------------
html_bad_date="$TMPDIR_LOCAL/bad-date.html"
cat > "$html_bad_date" <<'EOF'
<!DOCTYPE html><html><body>
<p>Срок сдачи: Q2 2026 <a href="https://setlgroup.ru/complex/riviera">setlgroup.ru</a></p>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_bad_date")
result=0
DELIVERY_DATE_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 3: DELIVERY_DATE_SKIP=1 → exit 0 (bypass)"
else
  fail "TEST 3: Expected exit 0 with bypass, got $result"
fi

# -----------------------------------------------------------------------
# TEST 4: Missing HTML file → graceful exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Bash","tool_input":{"command":"scp /tmp/nonexistent-dates-99999.html /tmp/dst/"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 4: Missing HTML → graceful exit 0"
else
  fail "TEST 4: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 5: Date in HTML but no adjacent URL within 600 chars → exit 0
# -----------------------------------------------------------------------
html_date_no_url="$TMPDIR_LOCAL/date-no-url.html"
cat > "$html_date_no_url" <<'EOF'
<!DOCTYPE html><html><body>
<h1>ЖК Северная Долина</h1>
<p>Срок сдачи: 2 кв. 2025 года</p>
<p>Студии от 4.5М рублей</p>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_date_no_url")
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 5: Date without source URL nearby → exit 0 (no pairs)"
else
  fail "TEST 5: Expected exit 0, got $result"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
