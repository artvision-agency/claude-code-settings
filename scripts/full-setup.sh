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

# 6. Разместить memory файлы
# Memory привязана к пути проекта — определяем автоматически
ARTVISION_DIR="$HOME/artvision-data"
if [ -d "$ARTVISION_DIR" ]; then
    # Путь memory = хэш от абсолютного пути проекта
    # Claude Code использует формат: ~/.claude/projects/-Users-username/memory/
    USERNAME=$(whoami)
    MEMORY_DIR="$HOME/.claude/projects/-Users-${USERNAME}/memory"
    mkdir -p "$MEMORY_DIR"
    if [ -d "$HOME/.claude/memory" ]; then
        echo "📝 Копирую memory файлы..."
        cp -n "$HOME/.claude/memory/"*.md "$MEMORY_DIR/" 2>/dev/null || true
        echo "   Memory: $MEMORY_DIR"
    fi
fi

# 7. Сделать скрипты исполняемыми
chmod +x "$HOME/.claude/hooks/"*.sh 2>/dev/null || true
chmod +x "$HOME/.claude/hooks/"*.py 2>/dev/null || true
chmod +x "$HOME/.claude/scripts/"*.sh 2>/dev/null || true
chmod +x "$HOME/.claude/statusline.sh" 2>/dev/null || true

# 7. Установить cc-update / cc-share команды
mkdir -p "$HOME/.local/bin"
SETTINGS_DIR="$HOME/claude-code-settings"
if [ ! -d "$SETTINGS_DIR" ]; then
    git clone https://github.com/artvision-agency/claude-code-settings.git "$SETTINGS_DIR"
fi
ln -sf "$SETTINGS_DIR/scripts/cc-update.sh" "$HOME/.local/bin/cc-update"
ln -sf "$SETTINGS_DIR/scripts/cc-share.sh" "$HOME/.local/bin/cc-share"
chmod +x "$SETTINGS_DIR/scripts/cc-update.sh" "$SETTINGS_DIR/scripts/cc-share.sh"

# 8b. Screaming Frog CLI wrapper (sf)
if [ -x "/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher" ]; then
    if [ ! -f "$HOME/.local/bin/sf" ]; then
        echo "🔍 Устанавливаю sf (Screaming Frog CLI wrapper)..."
        bash "$SETTINGS_DIR/scripts/install-sf-wrapper.sh"
    else
        echo "🔍 sf wrapper уже установлен"
    fi
else
    echo "⚠️  Screaming Frog не найден — sf wrapper пропущен (поставь приложение и перезапусти)"
fi

# Ensure ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
        if [ -f "$rc" ] && ! grep -q '.local/bin' "$rc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
    done
fi

# 8. Auto-bootstrap в .zshrc (чтобы на новой машине ничего не набирать)
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
    if [ -f "$rc" ] && ! grep -q "claude-code-settings" "$rc"; then
        cat >> "$rc" << 'RCEOF'

# Claude Code — auto-bootstrap (новая машина = автонастройка)
[ -d "$HOME/.claude/.git" ] || {
  git clone --depth 1 https://github.com/artvision-agency/claude-code-settings.git "$HOME/.claude" 2>/dev/null
  chmod +x "$HOME/.claude/hooks/"*.sh "$HOME/.claude/scripts/"*.sh 2>/dev/null
  echo "✅ Claude Code settings installed from git"
}
RCEOF
        echo "   Added auto-bootstrap to $rc"
    fi
done

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📦 Установлено:"
echo "   - 11 hooks (6 событий: Start, PreTool, PostTool, Compact, Stop)"
echo "   - 50+ skills (/seo-audit, /page-create, /goal, ...)"
echo "   - 24 plugins (Playwright, Asana, Context7, ...)"
echo "   - Statusline (ctx%, cost, branch)"
echo "   - Memory (lessons, revenue-goal, accounts)"
echo "   - agent-browser + playwright (E2E)"
echo ""
echo "📝 Конфиги:"
echo "   - CLAUDE.md: $HOME/.claude/CLAUDE.md"
echo "   - Settings: $HOME/.claude/settings.json"
echo "   - Hooks:    $HOME/.claude/hooks/ (11 scripts)"
echo ""
echo "🚀 Запусти 'claude' чтобы начать!"
