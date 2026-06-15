#!/usr/bin/env bash
# Тест pre-tool-codex-lifecycle-guard.sh — 3 кейса WARN + 3 кейса PASS-молча + bypass.
# Хук всегда exit 0 (warn-only) → проверяем по наличию/отсутствию [CODEX-LIFECYCLE] в stderr.
set -uo pipefail
HOOK="$(dirname "$0")/pre-tool-codex-lifecycle-guard.sh"
PASS=0; FAIL=0

run() { # $1=desc $2=expect(warn|silent) $3=json $4=env
  rm -f /tmp/codex-lifecycle-warned-* 2>/dev/null
  local err; err="$(printf '%s' "$3" | env ${4:-} bash "$HOOK" 2>&1 1>/dev/null)"
  local got="silent"; printf '%s' "$err" | grep -q 'CODEX-LIFECYCLE' && got="warn"
  if [ "$got" = "$2" ]; then echo "  ✅ $1"; PASS=$((PASS+1)); else echo "  ❌ $1 (ожидал $2, got $got)"; FAIL=$((FAIL+1)); fi
}

echo "== WARN (код в код-локациях) =="
run "py в scripts/"        warn   '{"session_id":"t1","tool_input":{"file_path":"/Users/antonk/artvision-data/scripts/foo.py"}}'
run "js в .claude/workflows" warn '{"session_id":"t2","tool_input":{"file_path":"/Users/antonk/.claude/workflows/bar.js"}}'
run "sh в .claude/hooks"    warn  '{"session_id":"t3","tool_input":{"file_path":"/Users/antonk/.claude/hooks/baz.sh"}}'

echo "== SILENT (не код / не код-локация / тест / bypass) =="
run "md-файл"              silent '{"session_id":"t4","tool_input":{"file_path":"/Users/antonk/artvision-data/scripts/README.md"}}'
run "py вне код-локаций"   silent '{"session_id":"t5","tool_input":{"file_path":"/Users/antonk/some/other/foo.py"}}'
run "тест-файл"            silent '{"session_id":"t6","tool_input":{"file_path":"/Users/antonk/artvision-data/scripts/test_foo.py"}}'
run "bypass env"           silent '{"session_id":"t7","tool_input":{"file_path":"/Users/antonk/artvision-data/scripts/foo.py"}}' "CODEX_LIFECYCLE_OK=1"

echo "== DEDUP (2-й раз молчит) =="
rm -f /tmp/codex-lifecycle-warned-* 2>/dev/null
J='{"session_id":"dd","tool_input":{"file_path":"/Users/antonk/artvision-data/scripts/foo.py"}}'
e1="$(printf '%s' "$J" | bash "$HOOK" 2>&1 1>/dev/null)"; printf '%s' "$e1" | grep -q CODEX-LIFECYCLE && echo "  ✅ 1-й раз warn" && PASS=$((PASS+1)) || { echo "  ❌ 1-й раз нет warn"; FAIL=$((FAIL+1)); }
e2="$(printf '%s' "$J" | bash "$HOOK" 2>&1 1>/dev/null)"; printf '%s' "$e2" | grep -q CODEX-LIFECYCLE && { echo "  ❌ 2-й раз warn (нет dedup)"; FAIL=$((FAIL+1)); } || { echo "  ✅ 2-й раз молчит (dedup)"; PASS=$((PASS+1)); }

echo ""; echo "ИТОГО: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
