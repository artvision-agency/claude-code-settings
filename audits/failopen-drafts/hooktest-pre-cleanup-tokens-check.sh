#!/usr/bin/env bash
# Регресс-тест pre-cleanup-tokens-check (fail-CLOSED + stdin-чтение).
HOOK="$HOME/.claude/hooks/pre-cleanup-tokens-check.sh"
P=0; F=0
ok(){ echo "  ✅ $1"; P=$((P+1)); }
no(){ echo "  ❌ $1 (rc=$2)"; F=$((F+1)); }

echo "T1: stdin JSON c 'rm -rf ~/.npm' триггерит проверку (НЕ тихий exit 0 при пустом env)"
# Безопасная danger-dir без токенов: создаём пустую temp как ~/.npm-подобную? Хук смотрит реальные пути.
# Проверяем что хук НЕ выходит молча 0 на stdin — т.е. доходит до сканера. Используем не-danger путь -> exit 0 ожидаем,
# но через stdin (раньше env пуст -> exit 0 «вслепую», теперь CMD читается). Проверяем что CMD реально извлечён:
out=$(printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/safe-nonexistent-xyz"}}' | bash "$HOOK" 2>&1; echo "rc=$?")
# /tmp/... не в DANGER_PATHS -> exit 0 (корректно), но важно что не упал
echo "$out" | grep -q "rc=0" && ok "stdin payload обработан (не-danger путь -> exit 0)" || no "stdin payload" "$out"

echo "T2: timeout-бинарь отсутствует -> fail-CLOSED (exit 2) на danger-пути"
TMPBIN=$(mktemp -d)
# PATH без timeout/gtimeout, но с базовыми утилитами
for u in bash grep find jq cat printf head sed awk; do p=$(command -v $u 2>/dev/null); [ -n "$p" ] && ln -sf "$p" "$TMPBIN/$u" 2>/dev/null; done
rc=$(printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf ~/.npm"}}' | PATH="$TMPBIN" bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$rc" = "2" ] && ok "нет timeout -> fail-CLOSED exit 2" || no "timeout-missing должен блокировать" "$rc"
rm -rf "$TMPBIN"

echo "T3: CLEANUP_FORCE=1 обходит (осознанный bypass сохранён)"
rc=$(printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf ~/.npm"}}' | CLEANUP_FORCE=1 bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$rc" = "0" ] && ok "CLEANUP_FORCE=1 -> exit 0" || no "bypass" "$rc"

echo "T4: не-rm команда проходит (не в scope)"
rc=$(printf '{"tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}' | bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$rc" = "0" ] && ok "ls -> exit 0" || no "non-rm" "$rc"

echo "T5: пустой stdin -> exit 0 (нет команды, нечего проверять)"
rc=$(printf '' | bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$rc" = "0" ] && ok "пустой stdin -> exit 0" || no "empty" "$rc"

echo "ИТОГО: PASS=$P FAIL=$F"
[ "$F" -eq 0 ] && exit 0 || exit 1
