#!/bin/bash
# Полная настройка Claude Code для нового аккаунта/машины
# Запуск: curl -sL https://raw.githubusercontent.com/artvision-agency/claude-code-settings/main/scripts/full-setup.sh | bash

set -e

echo "🚀 Полная настройка Claude Code..."

# 1. Клонировать настройки (если ещё нет)
if [ ! -d "$HOME/.claude/.git" ]; then
    echo "📥 Клонирую настройки..."
    rm -rf "$HOME/.claude"
    git clone https://github.com/artvision-agency/claude-code-settings.git "$HOME/.claude"
else
    echo "📥 Обновляю настройки..."
    cd "$HOME/.claude" && git pull
fi

# 2. Клонировать wshobson-agents (если ещё нет)
if [ ! -d "$HOME/wshobson-agents" ]; then
    echo "📥 Клонирую wshobson-agents..."
    git clone --depth 1 https://github.com/wshobson/agents.git "$HOME/wshobson-agents"
else
    echo "📥 Обновляю wshobson-agents..."
    cd "$HOME/wshobson-agents" && git pull
fi

# 3. Создать симлинк для marketplace
mkdir -p "$HOME/.claude/plugins/marketplaces"
if [ ! -L "$HOME/.claude/plugins/marketplaces/wshobson-agents" ]; then
    echo "🔗 Создаю симлинк для wshobson marketplace..."
    ln -sf "$HOME/wshobson-agents" "$HOME/.claude/plugins/marketplaces/wshobson-agents"
fi

# 4. Установить bun + agent-browser (E2E тесты, экономия 40% токенов vs Chrome DevTools MCP)
if ! command -v bun &>/dev/null; then
    echo "📥 Устанавливаю bun..."
    curl -fsSL https://bun.sh/install | bash
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
fi

if ! command -v agent-browser &>/dev/null; then
    echo "🌐 Устанавливаю agent-browser + playwright..."
    bun add -g agent-browser playwright
    bun pm -g trust agent-browser edgedriver 2>/dev/null || true
    echo "🌐 Устанавливаю Chromium для agent-browser..."
    agent-browser install
fi

# 5. Создать директорию для логов
mkdir -p "$HOME/.claude/session_logs"

# 6. Сделать скрипты исполняемыми
chmod +x "$HOME/.claude/hooks/"*.sh 2>/dev/null || true
chmod +x "$HOME/.claude/hooks/"*.py 2>/dev/null || true
chmod +x "$HOME/.claude/scripts/"*.sh 2>/dev/null || true

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📦 Установлено:"
echo "   - 199 агентов (VoltAgent + wshobson)"
echo "   - 33 плагина (official + wshobson)"
echo "   - Hooks для защиты токенов"
echo "   - Автологирование сессий"
echo "   - agent-browser + playwright (E2E тесты)"
echo ""
echo "📝 CLAUDE.md: $HOME/.claude/CLAUDE.md"
echo ""
echo "🚀 Запусти 'claude' чтобы начать!"
