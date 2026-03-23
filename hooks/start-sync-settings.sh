#!/bin/bash
# SessionStart: автоматически подтягивает свежие настройки из git
# Гарантия: все аккаунты на всех машинах получают одинаковые хуки/rules/skills

CLAUDE_DIR="$HOME/.claude"

# Только если это git-репо
if [ -d "$CLAUDE_DIR/.git" ]; then
    cd "$CLAUDE_DIR"

    # Тихий pull (не блокировать старт если нет сети)
    PULL_RESULT=$(git pull --ff-only origin main 2>&1) || true

    if echo "$PULL_RESULT" | grep -q "Already up to date"; then
        : # тишина
    elif echo "$PULL_RESULT" | grep -qE "files? changed"; then
        CHANGED=$(echo "$PULL_RESULT" | grep -oE '[0-9]+ files? changed')
        echo "⚙️ Settings updated: $CHANGED (from claude-code-settings)"

        # Сделать новые скрипты исполняемыми
        chmod +x "$CLAUDE_DIR/hooks/"*.sh 2>/dev/null || true
        chmod +x "$CLAUDE_DIR/scripts/"*.sh 2>/dev/null || true
    fi
fi
