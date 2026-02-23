#!/bin/bash
# run-tests.sh — обёртка для тестовых команд
# Экономит токены: при успехе 1 строка, при ошибке — полный вывод
#
# Использование:
#   run-tests.sh "Unit tests" "pnpm test:run"
#   run-tests.sh "Python tests" "pytest tests/ -x"
#   run-tests.sh "E2E" "pnpm test:e2e"
#
# Автоматически добавляет fail-fast (--bail/--x) если не указан

DESCRIPTION="${1:?Usage: run-tests.sh <description> <command>}"
COMMAND="${2:?Usage: run-tests.sh <description> <command>}"

# Добавляем fail-fast если ещё нет
add_bail() {
    local cmd="$1"

    # Уже есть --bail или -x — не трогаем
    if echo "$cmd" | grep -qE -- '--bail|-x|--failFast'; then
        echo "$cmd"
        return
    fi

    # vitest / pnpm test
    if echo "$cmd" | grep -qE 'vitest|test:run|test:unit|test:e2e'; then
        # Пробуем добавить --bail, если vitest не поддерживает — не страшно
        echo "$cmd --bail 1"
        return
    fi

    # jest
    if echo "$cmd" | grep -q 'jest'; then
        echo "$cmd --bail"
        return
    fi

    # pytest
    if echo "$cmd" | grep -q 'pytest'; then
        echo "$cmd -x"
        return
    fi

    # по умолчанию — как есть
    echo "$cmd"
}

BAIL_CMD=$(add_bail "$COMMAND")
TMP_FILE=$(mktemp)

# Запускаем: при успехе — 1 строка, при ошибке — полный вывод
if eval "$BAIL_CMD" > "$TMP_FILE" 2>&1; then
    printf "  ✓ %s\n" "$DESCRIPTION"
    rm -f "$TMP_FILE"
    exit 0
else
    EXIT_CODE=$?
    printf "  ✗ %s (exit code: %d)\n" "$DESCRIPTION" "$EXIT_CODE"
    echo "---"
    cat "$TMP_FILE"
    rm -f "$TMP_FILE"
    exit $EXIT_CODE
fi
