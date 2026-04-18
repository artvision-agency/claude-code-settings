#!/bin/bash
# Переключение между аккаунтами Claude Max
# Использование: switch-account.sh [just|adw]
set -euo pipefail

ACC1="justtrance@gmail.com"
ACC2="adw.artvision.pro@gmail.com"

# Текущий аккаунт
CURRENT=$(claude auth status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('email','unknown'))" 2>/dev/null || echo "unknown")

case "${1:-}" in
    just|justtrance|1)
        TARGET="$ACC1" ;;
    adw|artvision|2)
        TARGET="$ACC2" ;;
    "")
        # Без аргумента — переключить на другой
        if [ "$CURRENT" = "$ACC1" ]; then
            TARGET="$ACC2"
        else
            TARGET="$ACC1"
        fi ;;
    *)
        echo "Usage: $0 [just|adw]"
        echo "  just/1 → $ACC1"
        echo "  adw/2  → $ACC2"
        echo "  (пусто) → переключить на другой"
        exit 1 ;;
esac

if [ "$CURRENT" = "$TARGET" ]; then
    echo "Уже на $TARGET"
    exit 0
fi

echo "Переключаю: $CURRENT → $TARGET"
claude auth logout 2>/dev/null || true
claude auth login --email "$TARGET"
echo "Готово: $TARGET"
