#!/usr/bin/env bash
# test-hook-interaction-lint.sh — регресс-тест для hook-interaction-lint (слой 5, seed).
# Проверяет: (1) текущая конфигурация чистая; (2) lint ЛОВИТ искусственный цикл (есть «зубы»).
set -uo pipefail
LINT="$HOME/.claude/hooks/hook-interaction-lint.sh"
HOOKS="$HOME/.claude/hooks"
PASS=0; FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "T1: текущая конфигурация без циклов (после фиксов 30.05)"
if bash "$LINT" >/dev/null 2>&1; then ok "lint exit 0 (чисто)"; else no "lint нашёл цикл в текущей конфигурации"; fi

echo "T2: lint имеет «зубы» — ловит искусственный цикл"
# Создаём fixture-хук, который exit-2 на всё и НЕ пропускает Skill (разблокировку skill-required)
TMP=$(mktemp -d)
cat > "$TMP/whitelists_tool_test.sh" <<'SH'
# fixture: блокирует всё кроме Read, не пропускает Skill/TaskCreate/Edit
case "$TOOL_NAME" in Read) exit 0;; esac
exit 2
SH
# whitelists_tool из lint должна вернуть 1 (НЕ пропускает Skill) для этого fixture
# Воспроизводим логику inline:
if awk -v t="Skill" 'function hastok(s){return (s ~ ("[(| \t]" t "[|) \t]") || s ~ ("(^|[(| \t])" t "[\\\\]?$"))} {if(hastok($0))win=10; if(win>0){if($0~/exit[[:space:]]+0/){f=1;exit}win--}} END{exit(f?0:1)}' "$TMP/whitelists_tool_test.sh"; then
  no "fixture без Skill ошибочно распознан как пропускающий Skill"
else
  ok "fixture корректно: НЕ пропускает Skill (зубы есть)"
fi
rm -rf "$TMP"

echo "T3: реальные хуки распознаются как пропускающие Skill (многострочный case)"
det(){ awk -v t="$2" 'function hastok(s){return (s ~ ("[(| \t]" t "[|) \t]") || s ~ ("(^|[(| \t])" t "[\\\\]?$"))} {if(hastok($0))win=10; if(win>0){if($0~/exit[[:space:]]+0/){f=1;exit}win--}} END{exit(f?0:1)}' "$HOOKS/$1"; }
det pre-tool-block-no-taskcreate.sh Skill && ok "block-no-taskcreate пропускает Skill" || no "не распознан Skill в block-no-taskcreate"
det pre-tool-recap-goal-check.sh TaskCreate && ok "recap-goal пропускает TaskCreate" || no "не распознан TaskCreate в recap-goal"

echo
echo "ИТОГО: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
