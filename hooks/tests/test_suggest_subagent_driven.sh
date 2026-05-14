#!/usr/bin/env bash
set -uo pipefail

SCRIPT=~/.claude/hooks/pre-tool-suggest-subagent-driven.sh
PASS=0
FAIL=0

assert_silent() {
    local input="$1"
    local name="$2"
    local out
    out=$(echo "$input" | "$SCRIPT" 2>&1)
    if [ -z "$out" ]; then
        echo "✓ PASS: $name"
        ((PASS++))
    else
        echo "✗ FAIL: $name -- got: $out"
        ((FAIL++))
    fi
}

assert_nudge() {
    local input="$1"
    local name="$2"
    local out
    out=$(echo "$input" | "$SCRIPT" 2>&1)
    if echo "$out" | grep -q "SUGGESTED-SKILL"; then
        echo "✓ PASS: $name"
        ((PASS++))
    else
        echo "✗ FAIL: $name -- expected SUGGESTED-SKILL, got: $out"
        ((FAIL++))
    fi
}

# Test 1: short prompt → silent
TS1="test-session-1-$$"
rm -f /tmp/subagent-driven-nudged-$TS1
assert_silent "{\"session_id\":\"$TS1\",\"prompt\":\"привет\",\"transcript_path\":\"/nonexistent\"}" "short prompt silent"

# Test 2: long plan → nudge
TS2="test-session-2-$$"
rm -f /tmp/subagent-driven-nudged-$TS2
assert_nudge "{\"session_id\":\"$TS2\",\"prompt\":\"1. сделать X\\n2. потом Y\\n3. потом Z\\n4. потом W\",\"transcript_path\":\"/nonexistent\"}" "long plan nudge"

# Test 3: self-disable after first nudge
TS3="test-session-3-$$"
rm -f /tmp/subagent-driven-nudged-$TS3
echo "{\"session_id\":\"$TS3\",\"prompt\":\"1. X\\n2. Y\\n3. Z\",\"transcript_path\":\"/nonexistent\"}" | "$SCRIPT" >/dev/null 2>&1
assert_silent "{\"session_id\":\"$TS3\",\"prompt\":\"1. A\\n2. B\\n3. C\",\"transcript_path\":\"/nonexistent\"}" "self-disable after first nudge"

# Test 4: bullet list → nudge
TS4="test-session-4-$$"
rm -f /tmp/subagent-driven-nudged-$TS4
assert_nudge "{\"session_id\":\"$TS4\",\"prompt\":\"- сделать X\\n- потом Y\\n- потом Z\",\"transcript_path\":\"/nonexistent\"}" "bullet plan nudge"

# Cleanup
rm -f /tmp/subagent-driven-nudged-test-session-*

echo ""
echo "Results: $PASS PASS, $FAIL FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
