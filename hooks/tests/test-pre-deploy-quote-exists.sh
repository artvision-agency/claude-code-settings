#!/usr/bin/env bash
# Tests for pre-deploy-quote-exists.py
# Calls hook directly (bypasses Claude harness)
set -uo pipefail

HOOK_PY="$HOME/.claude/hooks/pre-deploy-quote-exists.py"
PASS=0
FAIL=0

ok() { echo "  [PASS] $1"; PASS=$(( PASS + 1 )); }
fail() { echo "  [FAIL] $1"; FAIL=$(( FAIL + 1 )); }

run_hook() {
  local payload="$1"
  local exit_code=0
  python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || exit_code=$?
  echo $exit_code
}

echo "=== pre-deploy-quote-exists.py ==="

# -----------------------------------------------------------------------
# TEST 1: HAPPY PATH — Bash tool (not Write/Edit) → hook ignores → exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Bash","tool_input":{"command":"scp file.html user@vps:/var/www/"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 1: Bash tool → hook skips → exit 0"
else
  fail "TEST 1: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 2: HAPPY PATH — Write to non-client path (/tmp) → hook ignores
# -----------------------------------------------------------------------
payload='{"tool_name":"Write","tool_input":{"file_path":"/tmp/scratch.html","content":"<html><body>test</body></html>"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 2: Write to /tmp (non-client path) → exit 0"
else
  fail "TEST 2: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 3: BYPASS — QUOTE_VERIFY_SKIP=1 → exit 0 regardless
# -----------------------------------------------------------------------
payload='{"tool_name":"Write","tool_input":{"file_path":"/Users/antonk/artvision-data/clients/test/presale/kp/test.html","content":"<html><body>«придуманная цитата дольщика средства заморозить» <a href=\"https://spbguru.ru/reviews/1\">spbguru</a></body></html>"}}'
result=0
QUOTE_VERIFY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 3: QUOTE_VERIFY_SKIP=1 → exit 0 (bypass works)"
else
  fail "TEST 3: Expected exit 0 with bypass, got $result"
fi

# -----------------------------------------------------------------------
# TEST 4: Write to client path but no quotes in HTML → exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Write","tool_input":{"file_path":"/Users/antonk/artvision-data/clients/test/kp/noquotes.html","content":"<html><body><p>Продаём квартиры. Цены от 5М.</p></body></html>"}}'
result=$(run_hook "$payload")
if [[ $result -eq 0 ]]; then
  ok "TEST 4: Client HTML with no quotes → exit 0"
else
  fail "TEST 4: Expected exit 0, got $result"
fi

# -----------------------------------------------------------------------
# TEST 5: Two quotes in client HTML with bypass → exit 0
# -----------------------------------------------------------------------
payload='{"tool_name":"Write","tool_input":{"file_path":"/Users/antonk/artvision-data/personal/test-quotes.html","content":"<html><body>«первая выдуманная цитата здесь пример» <a href=\"https://spbguru.ru/1\">src1</a><br>«вторая выдуманная цитата пример текст» <a href=\"https://spbguru.ru/2\">src2</a></body></html>"}}'
result=0
QUOTE_VERIFY_SKIP=1 python3 "$HOOK_PY" <<< "$payload" > /dev/null 2>&1 || result=$?
if [[ $result -eq 0 ]]; then
  ok "TEST 5: Two quotes with bypass → exit 0"
else
  fail "TEST 5: Expected exit 0, got $result"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
