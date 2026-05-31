#!/usr/bin/env bash
# Регресс-тест pre-scp-kp-strict-factcheck (fail-CLOSED).
HOOK="$HOME/.claude/hooks/pre-scp-kp-strict-factcheck.sh"
P=0; F=0
ok(){ echo "  ✅ $1"; P=$((P+1)); }
no(){ echo "  ❌ $1 (rc=$2)"; F=$((F+1)); }
run(){ printf '%s' "$1" | bash "$HOOK" >/dev/null 2>&1; echo $?; }

# KP-scp на несуществующий slug → нет factcheck-отчёта → ДОЛЖЕН блокировать (exit 2; раньше exit 1 = warn-only)
KP='{"tool_name":"Bash","tool_input":{"command":"scp /Users/antonk/artvision-data/presales/nonexistslugxyz/kp/v1.html root@80.90.181.152:/var/www/artvision/kp/nonexistslugxyz/"}}'
echo "T1: KP-scp без свежего factcheck-отчёта → exit 2 (fail-CLOSED, был warn-only exit1)"
rc=$(run "$KP"); [ "$rc" = "2" ] && ok "блокирует exit 2" || no "должен блокировать" "$rc"

echo "T2: malformed JSON → exit 2 (был exit 0)"
rc=$(run 'GARBAGE{{'); [ "$rc" = "2" ] && ok "malformed → exit 2" || no "malformed" "$rc"

echo "T3: не-KP scp (другой путь) → exit 0 (не в scope)"
rc=$(run '{"tool_name":"Bash","tool_input":{"command":"scp /tmp/file.txt root@80.90.181.152:/tmp/"}}'); [ "$rc" = "0" ] && ok "не-KP → exit 0" || no "non-KP" "$rc"

echo "T4: FACTCHECK_STRICT_SKIP=1 обходит KP-scp"
rc=$(printf '%s' "$KP" | FACTCHECK_STRICT_SKIP=1 bash "$HOOK" >/dev/null 2>&1; echo $?); [ "$rc" = "0" ] && ok "bypass → exit 0" || no "bypass" "$rc"

echo "T5: нет команды в payload → exit 0"
rc=$(run '{"tool_name":"Bash","tool_input":{}}'); [ "$rc" = "0" ] && ok "нет cmd → exit 0" || no "no-cmd" "$rc"

echo "ИТОГО: PASS=$P FAIL=$F"
[ "$F" -eq 0 ] && exit 0 || exit 1
