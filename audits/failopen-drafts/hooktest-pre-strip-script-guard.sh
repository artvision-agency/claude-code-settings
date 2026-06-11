#!/bin/bash
# hooktest-pre-strip-script-guard.sh
# Регресс-тест: доказывает что НОВЫЙ черновик блокирует (fail-CLOSED) stdin-only
# strip-payload, где СТАРЫЙ хук пропускал (exit 0). Плюс позитивные кейсы.
#
# ВАЖНО: тест НЕ трогает live-файл. Сравнивает поведение:
#   OLD = /Users/antonk/.claude/hooks/pre-strip-script-guard.sh (read-only прогон)
#   NEW = /tmp/hookfix-pre-strip-script-guard.sh

OLD="/Users/antonk/.claude/hooks/pre-strip-script-guard.sh"
NEW="/tmp/hookfix-pre-strip-script-guard.sh"

PASS=0
FAIL=0

# run_case <label> <hook> <stdin-payload> <env-prefix> <expected-exit-spec>
# expected-exit-spec: "==N" точное, "!=0" любой ненулевой, "==0" пропуск
run_case() {
  local label="$1" hook="$2" payload="$3" envpfx="$4" spec="$5"
  local rc
  # Запускаем хук в подоболочке, очищая env-переменные команды чтобы
  # эмулировать «только stdin» (как делает харнес при stdin-payload).
  rc=$(
    env -u CLAUDE_BASH_COMMAND -u TOOL_INPUT_COMMAND $envpfx \
      bash "$hook" <<<"$payload" >/dev/null 2>&1
    echo $?
  )
  local ok=0
  case "$spec" in
    "==0")  [ "$rc" -eq 0 ] && ok=1 ;;
    "!=0")  [ "$rc" -ne 0 ] && ok=1 ;;
    "==1")  [ "$rc" -eq 1 ] && ok=1 ;;
    "==2")  [ "$rc" -eq 2 ] && ok=1 ;;
  esac
  if [ "$ok" = "1" ]; then
    echo "PASS | $label | rc=$rc (expected $spec)"
    PASS=$((PASS+1))
  else
    echo "FAIL | $label | rc=$rc (expected $spec)"
    FAIL=$((FAIL+1))
  fi
}

echo "=================================================================="
echo " REGRESSION: stdin-only strip payload (the core bug)"
echo "=================================================================="

# Каноничный проблемный вход: strip-скрипт на clients/ БЕЗ --dry-run, через stdin.
DANGER_JSON='{"tool_name":"Bash","tool_input":{"command":"python clients/ant-partners/strip_inline_duplicates.py"}}'

# 1) СТАРЫЙ хук — демонстрируем что он ПРОПУСКАЛ (exit 0). Это и есть баг.
run_case "OLD пропускает stdin strip-payload (BUG)" "$OLD" "$DANGER_JSON" "" "==0"

# 2) НОВЫЙ черновик — обязан БЛОКИРОВАТЬ fail-CLOSED (exit 2).
run_case "NEW блокирует stdin strip-payload (exit 2)" "$NEW" "$DANGER_JSON" "" "==2"

echo
echo "=================================================================="
echo " FAIL-CLOSED: битый JSON / непарсящийся payload со strip-сигнатурой"
echo "=================================================================="

# Невалидный JSON, но содержит strip-сигнатуру на clients/ — fail-CLOSED.
BROKEN_JSON='{"tool_input": {"command": "python clients/x/clean_revision.py" '  # незакрытый JSON
run_case "NEW: битый JSON + strip-сигнатура -> блок (exit 2)" "$NEW" "$BROKEN_JSON" "" "==2"

# JSON валиден, но command в другом месте (структура не та) + strip-сигнатура в сыром payload.
WRONG_STRUCT='{"params":{"cmd":"python clients/x/fix_clean.py"}}'
run_case "NEW: command не найден, но payload опасен -> блок (exit 2)" "$NEW" "$WRONG_STRUCT" "" "==2"

echo
echo "=================================================================="
echo " POSITIVE: безопасные / нерелевантные входы должны ПРОХОДИТЬ"
echo "=================================================================="

# Безопасная команда (ls) через stdin — не наша зона, exit 0.
SAFE_JSON='{"tool_name":"Bash","tool_input":{"command":"ls -la clients/ant-partners/"}}'
run_case "NEW: безопасная ls -> проходит (exit 0)" "$NEW" "$SAFE_JSON" "" "==0"

# strip-скрипт, НО с --dry-run — легитимный первый прогон, exit 0.
DRYRUN_JSON='{"tool_name":"Bash","tool_input":{"command":"python clients/x/strip_inline_duplicates.py --dry-run"}}'
run_case "NEW: strip + --dry-run -> проходит (exit 0)" "$NEW" "$DRYRUN_JSON" "" "==0"

# strip-скрипт НЕ на clients/templates/artvision-data путях — вне зоны, exit 0.
OFFSCOPE_JSON='{"tool_name":"Bash","tool_input":{"command":"python /tmp/strip_test.py"}}'
run_case "NEW: strip вне clients/ путей -> проходит (exit 0)" "$NEW" "$OFFSCOPE_JSON" "" "==0"

# Невалидный JSON БЕЗ strip-сигнатуры — не наша зона, exit 0 (не блокируем чужое).
BROKEN_SAFE='{"tool_input": {"command": "echo hello" '
run_case "NEW: битый JSON без strip-сигнатуры -> проходит (exit 0)" "$NEW" "$BROKEN_SAFE" "" "==0"

# Пустой stdin — нечего проверять, exit 0.
run_case "NEW: пустой stdin -> проходит (exit 0)" "$NEW" "" "" "==0"

# Bypass STRIP_FORCE=1 на опасном payload — легитимный обход сохранён, exit 0.
run_case "NEW: STRIP_FORCE=1 bypass на strip-payload -> проходит (exit 0)" "$NEW" "$DANGER_JSON" "STRIP_FORCE=1" "==0"

echo
echo "=================================================================="
echo " BACKWARD-COMPAT: env-переменная команды (старый путь) всё ещё работает"
echo "=================================================================="

# Через env CLAUDE_BASH_COMMAND (как раньше) — strip без --dry-run должен блокировать.
rc=$(
  CLAUDE_BASH_COMMAND="python clients/x/strip_inline_duplicates.py" \
    bash "$NEW" </dev/null >/dev/null 2>&1
  echo $?
)
if [ "$rc" -ne 0 ]; then
  echo "PASS | NEW: env strip-команда -> блок | rc=$rc (expected !=0)"
  PASS=$((PASS+1))
else
  echo "FAIL | NEW: env strip-команда -> блок | rc=$rc (expected !=0)"
  FAIL=$((FAIL+1))
fi

echo
echo "=================================================================="
echo " ИТОГ: PASS=$PASS FAIL=$FAIL"
echo "=================================================================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
