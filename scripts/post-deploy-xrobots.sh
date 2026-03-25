#!/usr/bin/env bash
# post-deploy-xrobots.sh — Проверка X-Robots-Tag после деплоя на VPS
# Вызывается после scp на artvision.pro
# Использование: post-deploy-xrobots.sh <URL>
# Или автоматически из хука PostToolUse(Bash) при scp

set -euo pipefail

URL="${1:-}"

# Если вызван из хука — извлечь URL из команды
if [ -z "$URL" ] && [ -n "${CLAUDE_BASH_COMMAND:-}" ]; then
    # Извлекаем путь из scp: root@80.90.181.152:/var/www/artvision/XXX/
    REMOTE_PATH=$(echo "$CLAUDE_BASH_COMMAND" | grep -oE '/var/www/artvision/[^ ]+' | head -1)
    if [ -n "$REMOTE_PATH" ]; then
        # /var/www/artvision/mirbir-test/index.html → mirbir-test/
        REL_PATH=$(echo "$REMOTE_PATH" | sed 's|/var/www/artvision/||' | sed 's|/[^/]*$|/|')
        URL="https://artvision.pro/${REL_PATH}"
    fi
fi

if [ -z "$URL" ]; then
    exit 0  # Не наш случай
fi

# Проверяем X-Robots-Tag
HEADER=$(curl -sI --connect-timeout 5 --max-time 10 "$URL" 2>/dev/null | grep -i "x-robots-tag" || true)

if [ -z "$HEADER" ]; then
    echo ""
    echo "⚠️  X-ROBOTS-TAG ОТСУТСТВУЕТ: $URL"
    echo "    Страница может быть проиндексирована поисковиками!"
    echo "    Добавьте в nginx: add_header X-Robots-Tag \"noindex, nofollow\" always;"
    echo ""
    exit 0  # Предупреждение, не блок
else
    echo "✅ X-Robots-Tag: $URL → $(echo "$HEADER" | tr -d '\r')"
fi
