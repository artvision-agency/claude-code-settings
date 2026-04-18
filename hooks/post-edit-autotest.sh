#!/bin/bash
# PostToolUse (Edit/Write): авто-запуск тестов если есть тесты рядом с изменённым файлом
# + напоминание о verification/code-review при завершении крупного блока

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"
DIR=$(dirname "$FILE_PATH")
BASENAME=$(basename "$FILE_PATH" ".$EXT")

# Только для кодовых файлов
if [[ ! "$EXT" =~ ^(py|js|ts|jsx|tsx|mjs)$ ]]; then
  exit 0
fi

# Пропускаем тестовые файлы (чтобы не зацикливаться)
if echo "$BASENAME" | grep -q "^test_\|_test$\|\.test\|\.spec"; then
  exit 0
fi

# Пропускаем node_modules, .claude_temp_scripts
if echo "$FILE_PATH" | grep -q "node_modules\|\.claude_temp_scripts\|__pycache__"; then
  exit 0
fi

MESSAGES=""

# === Поиск тестов для этого файла ===
TESTS_FOUND=""

# Python: test_<name>.py в tests/ или рядом
if [ "$EXT" = "py" ]; then
  # Проверяем tests/ рядом
  if [ -f "$DIR/tests/test_${BASENAME}.py" ]; then
    TESTS_FOUND="$DIR/tests/test_${BASENAME}.py"
  elif [ -f "$DIR/test_${BASENAME}.py" ]; then
    TESTS_FOUND="$DIR/test_${BASENAME}.py"
  elif [ -d "$DIR/tests" ]; then
    # Есть папка tests/ но нет теста для этого файла
    MESSAGES="${MESSAGES}⚠️ Папка tests/ есть, но test_${BASENAME}.py не найден. Написать тесты?\n"
  fi
fi

# JS/TS: <name>.test.js или __tests__/<name>.test.js
if [[ "$EXT" =~ ^(js|ts|jsx|tsx)$ ]]; then
  if [ -f "$DIR/${BASENAME}.test.${EXT}" ]; then
    TESTS_FOUND="$DIR/${BASENAME}.test.${EXT}"
  elif [ -f "$DIR/__tests__/${BASENAME}.test.${EXT}" ]; then
    TESTS_FOUND="$DIR/__tests__/${BASENAME}.test.${EXT}"
  fi
fi

# Если тесты найдены — напомнить запустить
if [ -n "$TESTS_FOUND" ]; then
  MESSAGES="${MESSAGES}🧪 Тесты найдены: ${TESTS_FOUND}\n→ Запусти: pytest ${TESTS_FOUND} (или соответствующую команду)\n"
fi

# === Счётчик изменений в сессии (для напоминания о verification) ===
COUNTER_FILE="/tmp/claude_edit_counter_$$"
if [ -f "$COUNTER_FILE" ]; then
  COUNT=$(cat "$COUNTER_FILE")
  COUNT=$((COUNT + 1))
else
  COUNT=1
fi
echo "$COUNT" > "$COUNTER_FILE"

# После 10+ изменений — напомнить о verification
if [ "$COUNT" -eq 10 ]; then
  MESSAGES="${MESSAGES}📋 10+ файлов изменено в сессии. Рекомендую:\n→ /verification-loop — проверка всей работы\n→ /code-review — ревью изменений\n"
fi

# После 20+ — более настойчиво
if [ "$COUNT" -eq 20 ]; then
  MESSAGES="${MESSAGES}🔴 20+ изменений без verification! Обязательно запусти:\n→ superpowers:verification-before-completion\n→ superpowers:requesting-code-review\n"
fi

if [ -n "$MESSAGES" ]; then
  echo -e "$MESSAGES"
fi

exit 0
