#!/usr/bin/env bash
# Tests for pre-deploy-price-vs-source.py
# Calls hook directly (bypasses Claude harness)
set -uo pipefail

HOOK_PY="$HOME/.claude/hooks/pre-deploy-price-vs-source.py"
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

echo "=== pre-deploy-price-vs-source.py ==="

# -----------------------------------------------------------------------
# TEST 1: HAPPY PATH — no price+url pairs → exit 0
# -----------------------------------------------------------------------
html_no_prices="$TMPDIR_LOCAL/no-prices.html"
cat > "$html_no_prices" <<'EOF'
<!DOCTYPE html><html><body>
<h1>Каталог недвижимости</h1>
<p>Свяжитесь с нами для уточнения стоимости</p>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_no_prices")
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 1: No prices in HTML → exit 0"
else
  fail "TEST 1: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 2: HAPPY PATH — not scp command → hook skips → exit 0
# -----------------------------------------------------------------------
html_with_price="$TMPDIR_LOCAL/price.html"
cat > "$html_with_price" <<'EOF'
<!DOCTYPE html><html><body>
<p>Квартира от <strong>6.1М</strong> <a href="https://example.com/flat">Подробнее</a></p>
</body></html>
EOF

payload='{"tool_name":"Bash","tool_input":{"command":"git status"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 2: Non-scp command → hook skips → exit 0"
else
  fail "TEST 2: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 3: BYPASS — PRICE_VERIFY_SKIP=1 → exit 0
# -----------------------------------------------------------------------
html_bad_price="$TMPDIR_LOCAL/bad-price.html"
cat > "$html_bad_price" <<'EOF'
<!DOCTYPE html><html><body>
<p>Студия от <strong>6.1М</strong> <a href="https://cian.ru/sale/flat/123">cian.ru</a></p>
</body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_bad_price")
result=0
PRICE_VERIFY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 3: PRICE_VERIFY_SKIP=1 → exit 0 (bypass works)"
else
  fail "TEST 3: Expected exit 0 with bypass, got $result"
fi

# -----------------------------------------------------------------------
# TEST 4: Missing HTML file → graceful exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Bash","tool_input":{"command":"scp /tmp/nonexistent-prices-99999.html /tmp/dst/"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 4: Missing HTML → graceful exit 0"
else
  fail "TEST 4: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 5: Only CSS/static URLs near price → no false positive
# -----------------------------------------------------------------------
html_static_url="$TMPDIR_LOCAL/static.html"
cat > "$html_static_url" <<'EOF'
<!DOCTYPE html><html>
<head><link rel="stylesheet" href="https://cdn.example.com/main.css"></head>
<body><p>Студия от 6.1М</p></body></html>
EOF

payload=$(printf '{"tool_name":"Bash","tool_input":{"command":"scp %s /tmp/dst/"}}' "$html_static_url")
result=0
PRICE_VERIFY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 5: Static CSS URLs near price → no false positive"
else
  fail "TEST 5: Expected exit 0, got $result"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
