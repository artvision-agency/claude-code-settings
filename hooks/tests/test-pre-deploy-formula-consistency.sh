#!/usr/bin/env bash
# Tests for pre-deploy-formula-consistency.py
# Calls hook script directly with JSON on stdin (bypassing Claude harness)
set -uo pipefail

HOOK_PY="$HOME/.claude/hooks/pre-deploy-formula-consistency.py"
PASS=0
FAIL=0
TMPDIR_LOCAL=$(mktemp -d)

cleanup() { rm -rf -- "$TMPDIR_LOCAL"; }
trap cleanup EXIT

ok() { echo "  [PASS] $1"; PASS=$(( PASS + 1 )); }
fail() { echo "  [FAIL] $1"; FAIL=$(( FAIL + 1 )); }

run_hook() {
  # Usage: run_hook <json_payload> [env_var=val ...]
  local payload="$1"
  shift
  local exit_code=0
  env "$@" python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || exit_code=$?
  echo $exit_code
}

echo "=== pre-deploy-formula-consistency.py ==="

# -----------------------------------------------------------------------
# TEST 1: HAPPY PATH — HTML without K/мес headline → exit 0
# -----------------------------------------------------------------------
html_no_formula="$TMPDIR_LOCAL/no-formula.html"
cat > "$html_no_formula" <<'EOF'
<!DOCTYPE html><html><body>
<h1>Ипотечный калькулятор</h1>
<table><tr><td>35000</td><td>6000000</td></tr></table>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_no_formula")
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 1: No K/мес in headline → exit 0"
else
  fail "TEST 1: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 2: HAPPY PATH — consistent K (headline 5.83, table 5.83-5.875) → exit 0
# Pairs: 35000/6000000 = 5.833, 47000/8000000 = 5.875 → avg 5.854
# Headline 5.83 → deviation 0.41% → PASS
# -----------------------------------------------------------------------
html_consistent="$TMPDIR_LOCAL/consistent.html"
cat > "$html_consistent" <<'EOF'
<!DOCTYPE html><html><body>
<div class="rate-badge">5.83 К/мес × млн</div>
<table>
  <tr><th>Платёж</th><th>Кредит</th></tr>
  <tr><td>35000</td><td>6000000</td></tr>
  <tr><td>47000</td><td>8000000</td></tr>
</table>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_consistent")
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 2: Consistent K (5.83 headline, ~5.85 table) → exit 0"
else
  fail "TEST 2: Expected exit 0, got $result (false positive)"
fi

# -----------------------------------------------------------------------
# TEST 3: BLOCK — headline 7.0 К/мес, table gives ~5.83 → deviation 20% → exit 2
# -----------------------------------------------------------------------
html_conflict="$TMPDIR_LOCAL/conflict.html"
cat > "$html_conflict" <<'EOF'
<!DOCTYPE html><html><body>
<div class="rate-badge">7.0 К/мес × млн</div>
<table>
  <tr><td>35000</td><td>6000000</td></tr>
  <tr><td>47000</td><td>8000000</td></tr>
  <tr><td>58000</td><td>10000000</td></tr>
  <tr><td>70000</td><td>12000000</td></tr>
</table>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_conflict")
result=$(run_hook "$payload")
if [[ $result -eq 2 ]]; then
  ok "TEST 3: Headline K=7.0 vs table K≈5.83 → BLOCK (exit 2)"
else
  fail "TEST 3: Expected exit 2, got $result"
fi

# -----------------------------------------------------------------------
# TEST 4: BYPASS — FORMULA_CONSISTENCY_SKIP=1 → exit 0
# -----------------------------------------------------------------------
payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_conflict")
result=$(FORMULA_CONSISTENCY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1; echo $?)
if [[ $result -eq 0 ]]; then
  ok "TEST 4: FORMULA_CONSISTENCY_SKIP=1 → exit 0 (bypass)"
else
  fail "TEST 4: Expected exit 0 with bypass, got $result"
fi

# -----------------------------------------------------------------------
# TEST 5: Non-scp command → hook ignores → exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 5: git push command → hook skips → exit 0"
else
  fail "TEST 5: Expected exit 0, got $result"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
