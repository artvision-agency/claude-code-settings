#!/usr/bin/env bash
# run-all.sh — master test runner for anti-hallucination hooks
# Usage: bash ~/.claude/hooks/tests/run-all.sh
set -uo pipefail

TESTS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PASS_SUITES=0
FAIL_SUITES=0
# Note: set -e intentionally not used so all suites run regardless of failures

echo "============================================="
echo "  Anti-Hallucination Hooks — Test Runner"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================="
echo ""

run_suite() {
  local script="$1"
  local name
  name=$(basename "$script" .sh)

  if [[ ! -f "$script" ]]; then
    echo "[SKIP] $name — file not found"
    return
  fi

  echo "--- $name ---"
  if bash "$script"; then
    echo "[SUITE PASS] $name"
    PASS_SUITES=$(( PASS_SUITES + 1 ))
  else
    echo "[SUITE FAIL] $name"
    FAIL_SUITES=$(( FAIL_SUITES + 1 ))
  fi
  echo ""
}

run_suite "$TESTS_DIR/test-pre-deploy-coords-verify.sh"
run_suite "$TESTS_DIR/test-pre-deploy-price-vs-source.sh"
run_suite "$TESTS_DIR/test-pre-deploy-quote-exists.sh"
run_suite "$TESTS_DIR/test-pre-deploy-formula-consistency.sh"
run_suite "$TESTS_DIR/test-pre-deploy-delivery-date-source.sh"

# Also run any pre-existing tests
for f in "$TESTS_DIR"/test-*.sh; do
  name=$(basename "$f" .sh)
  # Skip already-run suites
  case "$name" in
    test-pre-deploy-coords-verify|\
    test-pre-deploy-price-vs-source|\
    test-pre-deploy-quote-exists|\
    test-pre-deploy-formula-consistency|\
    test-pre-deploy-delivery-date-source)
      continue ;;
  esac
  run_suite "$f"
done

echo "============================================="
echo "  TOTAL: $PASS_SUITES suites PASS, $FAIL_SUITES suites FAIL"
echo "============================================="

[[ $FAIL_SUITES -eq 0 ]] && exit 0 || exit 1
