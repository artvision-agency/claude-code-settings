#!/usr/bin/env bash
# Tests for pre-deploy-coords-verify.py
# Calls hook directly with heredoc JSON (bypasses Claude harness pre-outbound-gate)
set -uo pipefail

HOOK_PY="$HOME/.claude/hooks/pre-deploy-coords-verify.py"
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

echo "=== pre-deploy-coords-verify.py ==="

# -----------------------------------------------------------------------
# TEST 1: HAPPY PATH — no coordinates in HTML → exit 0
# -----------------------------------------------------------------------
html_no_coords="$TMPDIR_LOCAL/no-coords.html"
cat > "$html_no_coords" <<'EOF'
<!DOCTYPE html><html><body><h1>ЖК Ромашка</h1><p>Цена от 5М</p></body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_no_coords")
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 1: No coords in HTML → exit 0"
else
  fail "TEST 1: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 2: HAPPY PATH — non-scp command → hook ignores → exit 0
# -----------------------------------------------------------------------
html_with_coords="$TMPDIR_LOCAL/with-coords.html"
cat > "$html_with_coords" <<'EOF'
<!DOCTYPE html><html><body>
<iframe src="https://yandex.ru/maps?pt=30.3141,59.9396,pm2rdm&ll=30.3141,59.9396"></iframe>
</body></html>
EOF

payload='{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 2: Non-scp command → exit 0 (hook skips)"
else
  fail "TEST 2: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 3: BYPASS — COORDS_VERIFY_SKIP=1 → exit 0 even with coords in HTML
# -----------------------------------------------------------------------
html_bad="$TMPDIR_LOCAL/bad-coords.html"
cat > "$html_bad" <<'EOF'
<!DOCTYPE html><html><body>
<div data-name="Setl Riviera">
<iframe src="https://yandex.ru/maps?pt=30.494,59.875,pm2rdm"></iframe>
</div>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_bad")
result=0
COORDS_VERIFY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 3: COORDS_VERIFY_SKIP=1 → exit 0 (bypass works)"
else
  fail "TEST 3: Expected exit 0 with bypass, got $result"
fi

# -----------------------------------------------------------------------
# TEST 4: HTML file doesn't exist → graceful exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Bash","tool_input":{"command":"scp /tmp/nonexistent-99999.html /tmp/dst/"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 4: Missing HTML file → exit 0 (graceful)"
else
  fail "TEST 4: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 5: Valid coords in SPb bounding box + bypass → exit 0
# -----------------------------------------------------------------------
html_valid="$TMPDIR_LOCAL/valid-coords.html"
cat > "$html_valid" <<'EOF'
<!DOCTYPE html><html><body>
<div data-name="Петропавловская крепость">
<iframe src="https://yandex.ru/maps?pt=30.3167,59.9500,pm2rdm&z=14"></iframe>
</div>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_valid")
result=0
COORDS_VERIFY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 5: Valid SPb coords with bypass → exit 0"
else
  fail "TEST 5: Expected exit 0, got $result"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
