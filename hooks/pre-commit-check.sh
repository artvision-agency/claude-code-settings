#!/bin/bash
# PreToolUse (Bash): перед git commit — синтаксис + lint + тесты
# Блокирует коммит сломанного кода

COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

# Только для git commit
if ! echo "$COMMAND" | grep -qE "git\s+commit"; then
  exit 0
fi

ERRORS=""
WARNINGS=""

# Определяем репо
REPO_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$REPO_DIR" ] && exit 0

# Staged Python файлы — проверка синтаксиса
PY_FILES=$(cd "$REPO_DIR" && git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep '\.py$')
if [ -n "$PY_FILES" ]; then
  while IFS= read -r f; do
    FULL="$REPO_DIR/$f"
    if [ -f "$FULL" ]; then
      # Синтаксис
      SYNTAX=$(python3 -m py_compile "$FULL" 2>&1)
      if [ $? -ne 0 ]; then
        ERRORS="${ERRORS}🔴 SYNTAX ERROR: $f\n${SYNTAX}\n\n"
      fi

      # import без файла (базовая проверка)
      BAD_IMPORTS=$(grep -n "^from \.\." "$FULL" 2>/dev/null | head -3)
      if [ -n "$BAD_IMPORTS" ]; then
        WARNINGS="${WARNINGS}⚠️ Относительный import в $f:\n${BAD_IMPORTS}\n\n"
      fi
    fi
  done <<< "$PY_FILES"

  # Есть ли тесты для изменённых файлов? Если да — запустить
  while IFS= read -r f; do
    BASENAME=$(basename "$f" .py)
    DIR=$(dirname "$REPO_DIR/$f")
    TEST_FILE=""

    if [ -f "$DIR/tests/test_${BASENAME}.py" ]; then
      TEST_FILE="$DIR/tests/test_${BASENAME}.py"
    elif [ -f "$DIR/test_${BASENAME}.py" ]; then
      TEST_FILE="$DIR/test_${BASENAME}.py"
    fi

    if [ -n "$TEST_FILE" ]; then
      RESULT=$(cd "$REPO_DIR" && python3 -m pytest "$TEST_FILE" --tb=short -q 2>&1 | tail -5)
      if echo "$RESULT" | grep -qE "failed|error"; then
        ERRORS="${ERRORS}🔴 ТЕСТЫ ПАДАЮТ: $TEST_FILE\n${RESULT}\n\n"
      else
        echo "✅ Тесты прошли: $(basename $TEST_FILE)"
      fi
    fi
  done <<< "$PY_FILES"
fi

# Staged JS/TS — базовая проверка
JS_FILES=$(cd "$REPO_DIR" && git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.(js|ts|jsx|tsx)$' | grep -v node_modules)
if [ -n "$JS_FILES" ]; then
  while IFS= read -r f; do
    FULL="$REPO_DIR/$f"
    if [ -f "$FULL" ]; then
      # Проверка синтаксиса node
      SYNTAX=$(node --check "$FULL" 2>&1)
      if [ $? -ne 0 ]; then
        ERRORS="${ERRORS}🔴 SYNTAX ERROR: $f\n${SYNTAX}\n\n"
      fi
    fi
  done <<< "$JS_FILES"
fi

# Вывод
if [ -n "$ERRORS" ]; then
  echo "═══ PRE-COMMIT CHECK: БЛОКИРОВКА ═══"
  echo -e "$ERRORS"
  echo "Исправь ошибки перед коммитом."
  echo "═══════════════════════════════════"
  exit 2
fi

if [ -n "$WARNINGS" ]; then
  echo "--- Pre-commit warnings ---"
  echo -e "$WARNINGS"
  echo "---------------------------"
fi

exit 0
