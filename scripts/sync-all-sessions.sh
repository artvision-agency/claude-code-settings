#!/bin/bash
# Синхронизация всех проектов Artvision с git
# Использование: sync-all-sessions.sh [--push]

PROJECTS=(
    "/Users/antonk/artvision-data"
    "/Users/antonk/artvision-tg-bot"
    "/Users/antonk/devops-agent"
)

PUSH_FLAG="${1:-}"

echo "═══════════════════════════════════════════════════════"
echo "  SYNC ALL SESSIONS — $(date '+%Y-%m-%d %H:%M')"
echo "═══════════════════════════════════════════════════════"
echo ""

for project in "${PROJECTS[@]}"; do
    name=$(basename "$project")

    if [ ! -d "$project" ]; then
        echo "⚠️  $name — не найден"
        continue
    fi

    cd "$project" || continue

    echo "📁 $name"
    echo "───────────────────────────────────────"

    # Проверка git статуса
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "   ❌ Не git репозиторий"
        echo ""
        continue
    fi

    # Fetch remote
    git fetch origin 2>/dev/null

    # Проверка несинхронизированных изменений
    UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
    UNPUSHED=$(git log origin/main..HEAD 2>/dev/null | grep -c "^commit" || echo "0")
    SYNC_FILE="sync/SYNC_STATUS.md"

    if [ "$UNCOMMITTED" -gt 0 ]; then
        echo "   🔴 Незакоммичено: $UNCOMMITTED файлов"
        git status --porcelain | head -5 | sed 's/^/      /'
        [ "$UNCOMMITTED" -gt 5 ] && echo "      ... и ещё $((UNCOMMITTED-5))"
    else
        echo "   ✅ Всё закоммичено"
    fi

    if [ "$UNPUSHED" -gt 0 ]; then
        echo "   🟡 Не запушено: $UNPUSHED коммитов"
    fi

    # Проверка sync файла
    if [ -f "$SYNC_FILE" ]; then
        LAST_UPDATE=$(grep -m1 "Date:" "$SYNC_FILE" | sed 's/.*Date.*: //')
        echo "   📋 Последний sync: $LAST_UPDATE"
    else
        echo "   ⚠️  Нет $SYNC_FILE"
    fi

    # Автокоммит и пуш если флаг --push
    if [ "$PUSH_FLAG" = "--push" ] && [ "$UNCOMMITTED" -gt 0 ]; then
        echo "   ⏳ Коммичу и пушу..."
        git add -A
        git commit -m "sync: auto-sync $(date '+%Y-%m-%d %H:%M')

Co-Authored-By: Claude <noreply@anthropic.com>"
        git push origin main 2>/dev/null || git push origin master 2>/dev/null
        echo "   ✅ Запушено!"
    elif [ "$PUSH_FLAG" = "--push" ] && [ "$UNPUSHED" -gt 0 ]; then
        echo "   ⏳ Пушу..."
        git push origin main 2>/dev/null || git push origin master 2>/dev/null
        echo "   ✅ Запушено!"
    fi

    echo ""
done

echo "═══════════════════════════════════════════════════════"
if [ "$PUSH_FLAG" = "--push" ]; then
    echo "  ✅ Синхронизация завершена"
else
    echo "  💡 Добавь --push для автоматического коммита и пуша"
fi
echo "═══════════════════════════════════════════════════════"
